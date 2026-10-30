"""Curadoria protegida. Identidade e papeis validados pela API legada, nunca pelo cliente."""
import json
import os
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

from fastapi import APIRouter, Body, Depends, HTTPException
from fastapi.responses import Response
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, SecretStr, ValidationError

from .models import Principal,DocumentLink
from .workspace import Workspace, REVIEW_ROLES
from .review import progress,package,import_csv,preview_csv,locator,LocatorRequest
from .extraction import workflow,preview
from .synthesis import view as synthesis_view
from .full_collection import plan as collection_plan
from .identity import view as identity_view,preview as identity_preview,confirm as identity_confirm,LinkConfirmation
from .integrity import IntegrityConfirmation


def legacy_auth(path, token=None, payload=None):
    base=os.getenv("ANALYTICS_AUTH_URL", "http://127.0.0.1:18080").rstrip("/")
    headers={"Content-Type":"application/json"}
    if token: headers["Authorization"]="Bearer "+token
    request=Request(base+path,data=json.dumps(payload).encode() if payload else None,headers=headers)
    try:
        with urlopen(request,timeout=10) as response: return json.load(response)
    except HTTPError as error:
        raise HTTPException(401 if error.code in (400,401,403) else 503,"Autenticacao indisponivel ou credenciais invalidas") from None
    except (URLError,TimeoutError,ValueError): raise HTTPException(503,"Servico de autenticacao indisponivel") from None


class Login(BaseModel):
    email: str
    password: SecretStr


def router(root: Path, authenticate=None):
    routes=APIRouter(prefix="/api/clinical",tags=["Curadoria clinica protegida"])
    bearer=HTTPBearer(auto_error=False)

    def principal(credentials: HTTPAuthorizationCredentials | None=Depends(bearer)):
        if not credentials: raise HTTPException(401,"Autenticacao obrigatoria")
        if authenticate: return authenticate(credentials.credentials)
        me=legacy_auth("/api/auth/me",token=credentials.credentials)
        return Principal(str(me["id"]),tuple(me["roles"]))

    def workspace(key):
        try: return Workspace(root,key)
        except FileNotFoundError: raise HTTPException(404,"Espaco de curadoria inexistente") from None
        except ValueError: raise HTTPException(409,"Integridade do espaco de curadoria invalida") from None

    @routes.post("/login")
    def login(body: Login):
        return legacy_auth("/api/auth/login",payload={"email":body.email,"password":body.password.get_secret_value()})

    @routes.get("/workspaces")
    def listing(actor: Principal=Depends(principal)):
        actor.require(*REVIEW_ROLES)
        result=[]
        for folder in (root/"clinical").glob("*"):
            if (folder/"curation.sqlite3").is_file():
                current=workspace(folder.name)
                result.append(dict(id=folder.name,document_count=len(current.input.data["documents"]),created_at=current.input.data.get("createdAt"),
                    source_protocol={k:current.input.data.get("protocol",{}).get(k) for k in ("code","cutoff_date")}))
        return sorted(result,key=lambda r:(str(r["created_at"] or ""),r["id"]),reverse=True)

    @routes.get("/contracts")
    def contracts(actor: Principal=Depends(principal)):
        actor.require(*REVIEW_ROLES)
        from .models import Screen,Result,Review,Conclusion,DocumentLink,Calibration,Absence
        from .selection_flow import ExclusionReason
        from .integrity import IntegrityNotice,IntegrityConfirmation
        return {model.__name__:model.model_json_schema() for model in (Screen,Result,Review,Conclusion,DocumentLink,Calibration,Absence,ExclusionReason,IntegrityNotice,IntegrityConfirmation)}

    @routes.get("/{key}/state")
    def state(key: str, actor: Principal=Depends(principal)):
        try: return Response(content=json.dumps(workspace(key).private_state(actor),ensure_ascii=False),
            media_type="application/json",headers={"Cache-Control":"no-store"})
        except ValueError: raise HTTPException(409,"Integridade da curadoria invalida") from None

    @routes.get("/{key}/progress")
    def current_progress(key: str,actor: Principal=Depends(principal)):
        return Response(content=json.dumps(progress(workspace(key),actor),ensure_ascii=False),
            media_type="application/json",headers={"Cache-Control":"no-store"})

    @routes.get("/{key}/selection-flow")
    def selection_flow(key: str,actor: Principal=Depends(principal)):
        from .selection_flow import view
        try:
            return Response(content=json.dumps(view(workspace(key),actor),ensure_ascii=False),
                media_type="application/json",headers={"Cache-Control":"no-store"})
        except ValueError as error: raise HTTPException(409,str(error)) from None

    @routes.get("/{key}/selection-flow/export")
    def selection_flow_export(key: str,actor: Principal=Depends(principal)):
        from .selection_flow import export_summary
        try:
            return Response(content=json.dumps(export_summary(workspace(key),actor),ensure_ascii=False,sort_keys=True,indent=2),
                media_type="application/json",headers={"Cache-Control":"no-store",
                    "Content-Disposition":'attachment; filename="selection-flow.json"'})
        except ValueError as error: raise HTTPException(409,str(error)) from None

    @routes.get("/{key}/identity")
    def identity_state(key: str,actor: Principal=Depends(principal)):
        try:return identity_view(workspace(key),actor)
        except ValueError as error:raise HTTPException(409,str(error)) from None

    @routes.get("/{key}/integrity")
    def integrity_state(key: str,actor: Principal=Depends(principal)):
        from .integrity import view
        try:return Response(content=json.dumps(view(workspace(key),actor),ensure_ascii=False),media_type="application/json",headers={"Cache-Control":"no-store"})
        except ValueError as error:raise HTTPException(409,str(error)) from None

    @routes.post("/{key}/integrity/preview")
    def integrity_preview(key: str,payload: dict,actor: Principal=Depends(principal)):
        from .integrity import preview
        try:return preview(workspace(key),payload,actor)
        except ValidationError:raise HTTPException(422,"Campos do alerta documental invalidos") from None
        except ValueError as error:raise HTTPException(409,str(error)) from None

    @routes.post("/{key}/integrity/confirm")
    def integrity_confirm(key: str,request: IntegrityConfirmation,actor: Principal=Depends(principal)):
        from .integrity import confirm
        try:return confirm(workspace(key),request,actor)
        except ValueError as error:raise HTTPException(409,str(error)) from None

    @routes.post("/{key}/identity/preview")
    def preview_identity(key: str,payload: DocumentLink,actor: Principal=Depends(principal)):
        try:return identity_preview(workspace(key),payload.model_dump(),actor)
        except ValueError as error:raise HTTPException(409,str(error)) from None

    @routes.post("/{key}/identity/confirm")
    def confirm_identity(key: str,request: LinkConfirmation,actor: Principal=Depends(principal)):
        try:return identity_confirm(workspace(key),request,actor)
        except ValueError as error:raise HTTPException(409,str(error)) from None

    @routes.get("/{key}/extraction")
    def extraction_workflow(key: str,actor: Principal=Depends(principal)):
        try: return workflow(workspace(key),actor)
        except ValueError: raise HTTPException(409,"Integridade do fluxo de extracao invalida") from None

    @routes.get("/{key}/extraction-coverage")
    def extraction_coverage(key: str,actor: Principal=Depends(principal)):
        from .extraction_coverage import view
        try:return Response(content=json.dumps(view(workspace(key),actor),ensure_ascii=False),media_type="application/json",headers={"Cache-Control":"no-store"})
        except ValueError:raise HTTPException(409,"Integridade do mapa de extracao invalida") from None

    @routes.get("/{key}/extraction-coverage/export")
    def extraction_coverage_export(key: str,actor: Principal=Depends(principal)):
        from .extraction_coverage import package
        try:return Response(content=package(workspace(key),actor),media_type="application/zip",
            headers={"Cache-Control":"no-store","Content-Disposition":'attachment; filename="extraction-coverage.zip"'})
        except ValueError:raise HTTPException(409,"Integridade do mapa de extracao invalida") from None

    @routes.get("/{key}/synthesis")
    def synthesis_state(key: str,actor: Principal=Depends(principal)):
        try: return synthesis_view(workspace(key),actor)
        except ValueError: raise HTTPException(409,"Integridade da sintese invalida") from None

    @routes.get("/{key}/collection-plan")
    def full_collection_plan(key: str,actor: Principal=Depends(principal)):
        try:return collection_plan(workspace(key),actor)
        except ValueError:raise HTTPException(409,"Integridade do plano de coleta invalida") from None

    @routes.post("/{key}/results/preview")
    def result_preview(key: str,payload: dict,actor: Principal=Depends(principal)):
        try: return preview(workspace(key),payload,actor)
        except ValidationError: raise HTTPException(422,"Campos do resultado invalidos; preencha os dados e preserve ausencias") from None
        except ValueError as error: raise HTTPException(409,str(error)) from None

    @routes.get("/{key}/results/{result_id}/changes")
    def result_changes(key: str,result_id: str,actor: Principal=Depends(principal)):
        from .result_changes import view
        try:return Response(content=json.dumps(view(workspace(key),result_id,actor),ensure_ascii=False),
            media_type="application/json",headers={"Cache-Control":"no-store"})
        except ValueError as error:raise HTTPException(404 if str(error)=='RESULT_NOT_FOUND' else 409,str(error)) from None

    @routes.get("/{key}/review-package")
    def review_package(key: str,actor: Principal=Depends(principal)):
        content=package(workspace(key),actor)
        return Response(content,media_type="application/zip",headers={"Content-Disposition":'attachment; filename="independent-review.zip"',"Cache-Control":"no-store"})

    @routes.post("/{key}/screening/import")
    def import_reviews(key: str,content: bytes=Body(media_type="text/csv"),expected_preview: str | None=None,actor: Principal=Depends(principal)):
        try: return import_csv(workspace(key),content,actor,expected_preview=expected_preview)
        except ValueError as error: raise HTTPException(409,str(error)) from None

    @routes.post("/{key}/screening/preview")
    def preview_reviews(key: str,content: bytes=Body(media_type="text/csv"),actor: Principal=Depends(principal)):
        try:return preview_csv(workspace(key),content,actor)
        except ValueError as error:raise HTTPException(409,str(error)) from None

    @routes.post("/{key}/locators")
    def create_locator(key: str,request: LocatorRequest,actor: Principal=Depends(principal)):
        try: return locator(workspace(key),request,actor)
        except ValueError as error: raise HTTPException(409,str(error)) from None

    @routes.get("/{key}/sources/{version_id}")
    def source(key: str,version_id: str,actor: Principal=Depends(principal)):
        try: return workspace(key).source(version_id,actor)
        except ValueError: raise HTTPException(404,"Versao documental nao encontrada") from None

    @routes.get("/{key}/studies/{study_id}/dossier")
    def study_dossier(key: str,study_id: str,basis_hash: str | None=None,actor: Principal=Depends(principal)):
        from .dossier import view
        try:
            result=view(workspace(key),study_id,actor,expected_basis=basis_hash)
            return Response(content=json.dumps(result,ensure_ascii=False),media_type="application/json",
                headers={"Cache-Control":"no-store"})
        except ValueError as error:
            raise HTTPException(404 if str(error)=="UNKNOWN_STUDY" else 409,str(error)) from None

    @routes.post("/{key}/actions/{kind}")
    def action(key: str,kind: str,payload: dict,actor: Principal=Depends(principal)):
        try: return workspace(key).act(kind,payload,actor)
        except ValidationError: raise HTTPException(422,"Campos invalidos; consulte o contrato e preserve as ausencias") from None
        except ValueError as error: raise HTTPException(409,str(error)) from None

    return routes
