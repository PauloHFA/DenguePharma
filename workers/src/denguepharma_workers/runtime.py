"""Worker duravel: Outbox -> RabbitMQ -> MinIO -> rascunho revisavel.

Executar: python -m denguepharma_workers.runtime --env-file .env
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import io
import json
import logging
import os
import threading
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

import pika
import urllib3
from minio import Minio
from minio.error import S3Error

from .pipeline import extraction_payload, verify_document

LOG = logging.getLogger("denguepharma.pipeline")
QUEUE = "denguepharma.pipeline.v1"
DEAD_QUEUE = "denguepharma.pipeline.invalid.v1"
BUCKET = "denguepharma-corpus"


@dataclass(frozen=True)
class Settings:
    backend_url: str
    pipeline_token: str
    rabbit_host: str
    rabbit_port: int
    rabbit_user: str
    rabbit_password: str
    minio_endpoint: str
    minio_user: str
    minio_password: str
    minio_secure: bool = False

    @classmethod
    def from_env(cls):
        def required(name):
            value = os.environ.get(name, "").strip()
            if not value:
                raise ValueError(f"Configure {name}")
            return value
        token = required("PIPELINE_TOKEN")
        if len(token) < 32:
            raise ValueError("PIPELINE_TOKEN exige ao menos 32 caracteres")
        return cls(os.environ.get("BACKEND_URL", "http://localhost:8080").rstrip("/"), token,
                   os.environ.get("RABBITMQ_HOST", "localhost"), int(os.environ.get("RABBITMQ_PORT", "5672")),
                   required("RABBITMQ_USER"), required("RABBITMQ_PASSWORD"),
                   os.environ.get("MINIO_ENDPOINT", "localhost:9000"), required("MINIO_USER"), required("MINIO_PASSWORD"),
                   os.environ.get("MINIO_SECURE", "false").lower() == "true")


class ApiError(RuntimeError):
    def __init__(self, status: int):
        self.status = status
        super().__init__(f"PIPELINE_HTTP_{status}")


class Api:
    def __init__(self, settings: Settings):
        self.base = settings.backend_url + "/api/internal/pipeline"
        self.token = settings.pipeline_token

    def request(self, path, body=None, *, method=None, lease=None, binary=False):
        headers = {"X-Pipeline-Token": self.token, "Content-Type": "application/json"}
        if lease:
            headers["X-Lease-Token"] = str(lease)
        payload = None if body is None else json.dumps(body, ensure_ascii=False).encode("utf-8")
        request = Request(self.base + path, data=payload, headers=headers, method=method or ("POST" if body is not None else "GET"))
        try:
            with urlopen(request, timeout=30) as response:
                content = response.read()
        except HTTPError as error:
            error.close()
            raise ApiError(error.code) from None
        return content if binary else (json.loads(content) if content else None)


class ObjectStore:
    def __init__(self, settings: Settings):
        self.client = Minio(settings.minio_endpoint, access_key=settings.minio_user, secret_key=settings.minio_password,
                            secure=settings.minio_secure,
                            http_client=urllib3.PoolManager(timeout=urllib3.Timeout(connect=5, read=20), retries=0))

    def ensure_bucket(self):
        if not self.client.bucket_exists(BUCKET):
            try:
                self.client.make_bucket(BUCKET)
            except S3Error as error:
                if error.code not in {"BucketAlreadyOwnedByYou", "BucketAlreadyExists"}:
                    raise

    def read(self, key):
        response = self.client.get_object(BUCKET, key)
        try:
            return response.read()
        finally:
            response.close()
            response.release_conn()

    def put_verified(self, key, content: bytes, expected_hash: str, content_type="application/json"):
        if hashlib.sha256(content).hexdigest() != expected_hash:
            raise ValueError("OBJECT_HASH_MISMATCH")
        try:
            existing = self.read(key)
        except S3Error as error:
            if error.code != "NoSuchKey":
                raise
            self.client.put_object(BUCKET, key, io.BytesIO(content), len(content), content_type=content_type)
            existing = self.read(key)
        if hashlib.sha256(existing).hexdigest() != expected_hash:
            # Nunca sobrescrever objeto divergente existente.
            raise ValueError("STORED_OBJECT_CORRUPTED")
        return existing


class LeaseKeeper:
    def __init__(self, api, job, token):
        self.api, self.job, self.token = api, job, token
        self.stop = threading.Event()
        self.lost = threading.Event()
        self.thread = threading.Thread(target=self._run, daemon=True)

    def _run(self):
        while not self.stop.wait(30):
            try:
                self.api.request(f"/jobs/{self.job}/renew", {"leaseToken": self.token})
            except Exception:
                self.lost.set()
                return

    def __enter__(self):
        self.thread.start()
        return self

    def check(self):
        if self.lost.is_set():
            raise RuntimeError("LEASE_RENEWAL_FAILED")

    def __exit__(self, *_):
        self.stop.set()
        self.thread.join(timeout=31)


class Worker:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.api = Api(settings)
        self.store = ObjectStore(settings)
        self.connection = None
        self.channel = None

    def connect(self):
        self.connection = pika.BlockingConnection(pika.ConnectionParameters(
            self.settings.rabbit_host, self.settings.rabbit_port,
            credentials=pika.PlainCredentials(self.settings.rabbit_user, self.settings.rabbit_password),
            heartbeat=300, blocked_connection_timeout=15, socket_timeout=10, stack_timeout=15))
        self.channel = self.connection.channel()
        self.channel.queue_declare(queue=DEAD_QUEUE, durable=True)
        self.channel.queue_declare(queue=QUEUE, durable=True, arguments={
            "x-max-priority": 10, "x-dead-letter-exchange": "", "x-dead-letter-routing-key": DEAD_QUEUE})
        self.channel.confirm_delivery()
        self.store.ensure_bucket()

    def close(self):
        if self.connection and self.connection.is_open:
            self.connection.close()

    def dispatch(self):
        events = self.api.request("/outbox/claim?limit=20", {})
        for event in events:
            event_id = str(event["event_id"])
            lease = {"leaseToken": str(event["relay_token"])}
            try:
                # Envelope apenas com referencias. Payload e tipo sao lidos da Outbox autorizada.
                self.channel.basic_publish(exchange="", routing_key=QUEUE, mandatory=True,
                    body=json.dumps({"eventId": event_id, "schemaVersion": event["schema_version"]}).encode(),
                    properties=pika.BasicProperties(content_type="application/json", delivery_mode=2,
                                                    message_id=event_id, priority=max(0, min(10, event["priority"]))))
                self.api.request(f"/outbox/{event_id}/confirm", lease)
            except Exception:
                try:
                    self.api.request(f"/outbox/{event_id}/fail", lease)
                except Exception:
                    pass  # A reserva expira e permite nova publicacao com o mesmo event_id.
                raise
        return len(events)

    def consume_one(self):
        method, properties, body = self.channel.basic_get(QUEUE, auto_ack=False)
        if method is None:
            return False
        try:
            envelope = json.loads(body)
            event_id = str(uuid.UUID(envelope["eventId"]))
            if envelope.get("schemaVersion") != 1:
                raise ValueError("SCHEMA_INVALID")
        except (ValueError, KeyError, TypeError, AttributeError):
            self.channel.basic_nack(method.delivery_tag, requeue=False)
            return True
        try:
            claim = self.api.request("/deliveries/claim", {"eventId": event_id})
        except ApiError as error:
            if error.status in {404, 409, 422}:
                self.channel.basic_nack(method.delivery_tag, requeue=False)
                return True
            raise
        if claim["state"] != "LEASED":
            # COMPLETED/QUARANTINED: terminal. BUSY: outro executor ou backoff; Outbox recupera lease expirado.
            self.channel.basic_ack(method.delivery_tag)
            return True
        job, token = claim["jobId"], claim["leaseToken"]
        try:
            with LeaseKeeper(self.api, job, token) as keeper:
                data = self.api.request(f"/jobs/{job}/input", lease=token)
                if claim["jobType"] == "EXTRACT_DOCUMENT":
                    content = data["content"].encode("utf-8")
                    verify_document(content, data["content_hash"])
                    uri = urlparse(data["storage_uri"])
                    if uri.scheme != "s3" or uri.netloc != BUCKET:
                        raise ValueError("STORAGE_URI_INVALID")
                    stored = self.store.put_verified(uri.path.lstrip("/"), content, data["content_hash"])
                    self.api.request(f"/jobs/{job}/archive", {"leaseToken": token, "contentHash": data["content_hash"], "sizeBytes": len(stored)})
                    output = extraction_payload(claim["refId"], verify_document(stored, data["content_hash"]))
                    keeper.check()
                    self.api.request(f"/jobs/{job}/extraction", {"leaseToken": token, "extraction": output})
                elif claim["jobType"] == "ANALYZE_EVIDENCE":
                    from .analysis import bundle
                    content = data["content"].encode("utf-8")
                    if hashlib.sha256(content).hexdigest() != data["content_hash"]:
                        raise ValueError("ANALYSIS_INPUT_HASH_MISMATCH")
                    files = bundle(content)
                    for name, artifact in files.items():
                        digest = hashlib.sha256(artifact).hexdigest()
                        key = f"analyses/{claim['refId']}/{digest}/{name}"
                        self.store.put_verified(key, artifact, digest, "application/octet-stream")
                    keeper.check()
                    self.api.request(f"/jobs/{job}/analysis", {"leaseToken": token,
                                     "bundleBase64": base64.b64encode(files["bundle.zip"]).decode("ascii")})
                elif claim["jobType"] == "GENERATE_REPORT":
                    artifacts = []
                    for format_ in ("pdf", "csv", "json"):
                        content = self.api.request(f"/jobs/{job}/report/{format_}", lease=token, binary=True)
                        digest = hashlib.sha256(content).hexdigest()
                        key = f"reports/{claim['refId']}/{digest}.{format_}"
                        self.store.put_verified(key, content, digest, {"pdf": "application/pdf", "csv": "text/csv", "json": "application/json"}[format_])
                        artifacts.append({"format": format_, "contentHash": digest, "sizeBytes": len(content)})
                    keeper.check()
                    self.api.request(f"/jobs/{job}/report", {"leaseToken": token, "artifacts": artifacts})
                else:
                    raise ValueError("UNSUPPORTED_JOB_TYPE")
            self.channel.basic_ack(method.delivery_tag)
            LOG.info("job=%s concluido", job)
        except Exception as error:
            if isinstance(error, ApiError) and error.status == 409:
                # Executor obsoleto nao altera job novo; o lease/outbox garantem recuperacao.
                self.channel.basic_ack(method.delivery_tag)
                return True
            self.api.request(f"/jobs/{job}/fail", {"leaseToken": token, "errorCode": "PROCESSING_FAILED"})
            self.channel.basic_ack(method.delivery_tag)
            LOG.warning("job=%s falhou tipo=%s; retentativa controlada pelo banco", job, type(error).__name__)
        return True

    def tick(self):
        published = self.dispatch()
        consumed = self.consume_one()
        self.connection.process_data_events(time_limit=0)
        return published or consumed


def load_env(path: str):
    for line in Path(path).read_text(encoding="utf-8-sig").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env-file")
    parser.add_argument("--once", action="store_true", help="Uma rodada de publicacao e consumo")
    args = parser.parse_args()
    if args.env_file:
        load_env(args.env_file)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    settings = Settings.from_env()
    while True:
        worker = Worker(settings)
        try:
            worker.connect()
            while True:
                active = worker.tick()
                if args.once:
                    return
                if not active:
                    worker.connection.sleep(1)
        except KeyboardInterrupt:
            return
        except Exception as error:
            LOG.warning("Pipeline indisponivel tipo=%s; reconectando em 5s", type(error).__name__)
            if args.once:
                raise SystemExit(1) from None
            time.sleep(5)
        finally:
            try:
                worker.close()
            except Exception:
                pass


if __name__ == "__main__":
    main()
