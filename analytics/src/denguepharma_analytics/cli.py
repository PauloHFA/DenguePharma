from __future__ import annotations

import argparse
import json
from pathlib import Path
from .sources.snapshot import from_file
from .storage import default_root, export, publish, verify_run


def main():
    parser = argparse.ArgumentParser(description="DenguePharma Analytics — migracao paralela somente de leitura")
    parser.add_argument("--data-dir", type=Path, default=None)
    commands = parser.add_subparsers(dest="command", required=True)
    snapshot_command=commands.add_parser("snapshot-collection");snapshot_command.add_argument("--protocol",required=True);snapshot_command.add_argument("--run-id",action="append",required=True);snapshot_command.add_argument("--output",type=Path,required=True);snapshot_command.add_argument("--env-file",type=Path,default=Path(".env"))
    compare_command=commands.add_parser("compare");compare_command.add_argument("--baseline",required=True);compare_command.add_argument("--current",required=True);compare_command.add_argument("--output",type=Path)
    prepare = commands.add_parser("prepare"); source = prepare.add_mutually_exclusive_group(required=True)
    source.add_argument("--input", type=Path); source.add_argument("--legacy-analysis")
    prepare.add_argument("--expected-hash"); prepare.add_argument("--env-file", type=Path, default=Path(".env"))
    for name in ("publish", "verify", "report"):
        command = commands.add_parser(name); command.add_argument("--run", required=True)
        if name == "report": command.add_argument("--quarto")
    serve = commands.add_parser("serve"); serve.add_argument("--host", default="127.0.0.1"); serve.add_argument("--port", type=int, default=18081)
    clinical=commands.add_parser("clinical-init"); clinical.add_argument("--input",type=Path,required=True); clinical.add_argument("--protocol",type=Path,required=True)
    backup_command=commands.add_parser("clinical-backup");backup_command.add_argument("--workspace",required=True);backup_command.add_argument("--output",type=Path,required=True)
    restore_command=commands.add_parser("clinical-restore");restore_command.add_argument("--input",type=Path,required=True);restore_command.add_argument("--expected-hash",required=True)
    collection=commands.add_parser("clinical-collect-pilot"); collection.add_argument("--protocol",type=Path,required=True); collection.add_argument("--cutoff",required=True); collection.add_argument("--output",type=Path,required=True); collection.add_argument("--env-file",type=Path,default=Path(".env"))
    for name in ("clinical-collection-plan","clinical-collect-full"):
        collection_command=commands.add_parser(name);collection_command.add_argument("--workspace",required=True)
        if name=="clinical-collect-full":
            collection_command.add_argument("--collection",required=True);collection_command.add_argument("--resume-failed",action="store_true");collection_command.add_argument("--recover-id");collection_command.add_argument("--env-file",type=Path,default=Path(".env"))
    for name in ("clinical-freeze","clinical-enrich","clinical-progress","clinical-review-package"):
        command=commands.add_parser(name); command.add_argument("--workspace",required=True)
        if name=="clinical-enrich": command.add_argument("--env-file",type=Path,default=Path(".env"))
        if name=="clinical-review-package": command.add_argument("--output",type=Path,required=True)
    args = parser.parse_args(); root = (args.data_dir or default_root()).resolve()
    if args.command=="snapshot-collection":
        from .sources.postgres import load_env
        from .sources.collection_snapshot import snapshot_from_runs
        from .clinical.full_collection import immutable_write
        if args.output.exists():raise ValueError("SNAPSHOT_OUTPUT_EXISTS")
        load_env(args.env_file);snapshot=snapshot_from_runs(args.protocol,args.run_id)
        args.output.parent.mkdir(parents=True,exist_ok=True);immutable_write(args.output,snapshot.content)
        print(json.dumps(dict(input_hash=snapshot.input_hash,documents=len(snapshot.data["documents"]),output=str(args.output),metadata_only=True),indent=2))
    elif args.command=="compare":
        from .comparison import compare,export as export_comparison
        result=compare(root,args.baseline,args.current)
        if args.output:print(json.dumps(export_comparison(result,args.output),indent=2))
        else:print(json.dumps(result,indent=2,ensure_ascii=True))
    elif args.command == "prepare":
        if args.input: snapshot = from_file(args.input, args.expected_hash)
        else:
            from .sources.postgres import from_postgres, load_env
            if args.env_file.exists(): load_env(args.env_file)
            snapshot = from_postgres(args.legacy_analysis)
        manifest = export(snapshot, root)
        print(json.dumps({"run_id": manifest["run_id"], "input_hash": manifest["input_hash"], "documents": manifest["tables"]["silver_documents"]["rows"],
                          "reviewed_studies": manifest["tables"]["mart_panorama"]["rows"]}, indent=2))
    elif args.command == "publish": print(json.dumps(publish(root, args.run), indent=2))
    elif args.command == "verify":
        result = verify_run(root, args.run); print(json.dumps({"run_id": args.run, "status": "OK", "tables": len(result["tables"])}))
    elif args.command == "report":
        from .reports.render import render
        print(json.dumps(render(root, args.run, args.quarto), indent=2))
    elif args.command=="clinical-collect-pilot":
        from .clinical.collection import collect
        from .sources.postgres import load_env
        load_env(args.env_file)
        print(json.dumps(collect(json.loads(args.protocol.read_bytes()),args.cutoff,args.output),indent=2))
    elif args.command in {"clinical-collection-plan","clinical-collect-full"}:
        from .clinical.workspace import Workspace
        from .clinical.models import Principal
        from .clinical.full_collection import plan,advance
        workspace=Workspace(root,args.workspace)
        if args.command=="clinical-collection-plan":result=plan(workspace,Principal("LOCAL_READ_ONLY_OPERATOR",("ADMINISTRADOR",)))
        else:
            from .sources.postgres import load_env
            load_env(args.env_file)
            result=advance(workspace,args.collection,resume_failed=args.resume_failed,recover_id=args.recover_id)
        print(json.dumps(result,indent=2,ensure_ascii=True))
    elif args.command in {"clinical-backup","clinical-restore"}:
        from .clinical.backup import backup,restore
        if args.command=="clinical-backup":
            from .clinical.workspace import Workspace
            result=backup(Workspace(root,args.workspace),args.output)
        else:result=restore(args.input,root,args.expected_hash)
        print(json.dumps(result,indent=2,ensure_ascii=True))
    elif args.command=="clinical-init":
        from .clinical.workspace import create
        workspace=create(root,from_file(args.input),json.loads(args.protocol.read_bytes()))
        print(json.dumps({"workspace_id":workspace.key,"clinical":workspace.freeze()["screening"]},indent=2))
    elif args.command=="clinical-enrich":
        from .clinical.workspace import Workspace
        from .clinical.sources import enrich
        from .sources.postgres import load_env
        load_env(args.env_file)
        print(json.dumps(enrich(Workspace(root,args.workspace)),indent=2))
    elif args.command in {"clinical-progress","clinical-review-package"}:
        from .clinical.workspace import Workspace
        from .clinical.models import Principal
        from .clinical.review import progress,package
        workspace=Workspace(root,args.workspace); operator=Principal("LOCAL_READ_ONLY_OPERATOR",("ADMINISTRADOR",))
        if args.command=="clinical-progress": print(json.dumps(progress(workspace,operator),indent=2,ensure_ascii=True))
        else:
            content=package(workspace,operator); args.output.parent.mkdir(parents=True,exist_ok=True)
            try:
                with args.output.open("xb") as stream: stream.write(content)
            except FileExistsError:
                if args.output.read_bytes()!=content: raise ValueError("REVIEW_PACKAGE_EXISTS_USE_NEW_OUTPUT")
            from .domain import digest
            print(json.dumps(dict(workspace_id=workspace.key,package_hash=digest(content),bytes=len(content)),indent=2))
    elif args.command=="clinical-freeze":
        from .clinical.workspace import Workspace
        workspace=Workspace(root,args.workspace); snapshot=workspace.snapshot(); manifest=export(snapshot,root)
        print(json.dumps({"run_id":manifest["run_id"],"input_hash":manifest["input_hash"],"clinical_results":manifest["tables"]["clinical_results"]["rows"]},indent=2))
    else:
        import uvicorn
        from .api import create_app
        uvicorn.run(create_app(root), host=args.host, port=args.port)


if __name__ == "__main__": main()
