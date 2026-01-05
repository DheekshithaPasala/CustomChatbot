from fastapi import APIRouter, Header, Query, HTTPException
import requests
import base64
import urllib.parse
from urllib.parse import urlparse

router = APIRouter(prefix="/files")
GRAPH_BASE = "https://graph.microsoft.com/v1.0"


# ------------------------------
# UTIL
# ------------------------------
def graph_get(url, token, not_found_message="Resource not found"):
    res = requests.get(url, headers={"Authorization": token})

    if res.status_code == 200:
        return res.json()

    if res.status_code == 401:
        raise HTTPException(401, detail="Invalid or expired token")

    if res.status_code == 403:
        raise HTTPException(403, detail="You do not have permission to access this resource")

    if res.status_code == 404:
        raise HTTPException(404, detail=not_found_message)

    raise HTTPException(400, detail=res.text)


def encode_share_url(url: str):
    encoded = base64.urlsafe_b64encode(url.encode()).decode().rstrip("=")
    return f"u!{encoded}"


def resolve_share_link(folder_url: str, token: str):
    encoded = encode_share_url(folder_url)
    share_api = f"{GRAPH_BASE}/shares/{encoded}/driveItem"
    res = requests.get(share_api, headers={"Authorization": token})

    if res.status_code == 200:
        return res.json()

    if res.status_code == 403:
        raise HTTPException(403, detail="You do not have access to this shared link")

    return None


def resolve_site_by_hostname(hostname: str, token: str):
    api = f"{GRAPH_BASE}/sites/{hostname}:/"
    return graph_get(api, token, "Unable to resolve SharePoint site")


def get_permissions(drive_id, item_id, token):
    url = f"{GRAPH_BASE}/drives/{drive_id}/items/{item_id}/permissions"
    return graph_get(url, token)


def extract_roles(perm_json):
    roles = set()
    for p in perm_json.get("value", []):
        for role in p.get("roles", []):
            roles.add(role.lower())

    return {
        "roles": list(roles),
        "canRead": "read" in roles or "write" in roles,
        "canWrite": "write" in roles
    }


# ------------------------------
# CHILDREN FETCH
# ------------------------------
@router.get("/children")
def get_children(drive_id: str, item_id: str, authorization: str = Header(...)):
    token = authorization
    api = f"{GRAPH_BASE}/drives/{drive_id}/items/{item_id}/children"

    children = graph_get(api, token, "Folder not found or inaccessible")

    items = []

    for f in children.get("value", []):
        fid = f["id"]

        perms = get_permissions(drive_id, fid, token)
        role_info = extract_roles(perms)

        items.append({
            "id": fid,
            "name": f["name"],
            "type": "folder" if "folder" in f else "file",
            "drive_id": drive_id,
            **role_info
        })

    return {
        "drive_id": drive_id,
        "items": items
    }


# ------------------------------
# MAIN ENTRY: by-path
# ------------------------------
@router.get("/by-path")
def get_files_by_path(folder_path: str = Query(""), authorization: str = Header(...)):
    token = authorization

    # ------------------ CASE 1: URL ------------------
    if folder_path.startswith("http"):

        # ✅ ALWAYS treat OneDrive-style shared links as shared links
        if "/:f:/" in folder_path or "/:u:/" in folder_path:
            share_res = resolve_share_link(folder_path, token)

            if not share_res:
                raise HTTPException(404, detail="Unable to resolve shared OneDrive link")

            drive_id = share_res["parentReference"]["driveId"]
            item_id = share_res["id"]

            # If file
            if "file" in share_res:
                perms = get_permissions(drive_id, item_id, token)
                role_info = extract_roles(perms)

                return {
                    "drive_id": drive_id,
                    "items": [{
                        "id": item_id,
                        "name": share_res["name"],
                        "type": "file",
                        "drive_id": drive_id,
                        **role_info
                    }]
                }

            # Folder → fetch children
            children_api = f"{GRAPH_BASE}/drives/{drive_id}/items/{item_id}/children"
            children = graph_get(children_api, token)

            items = []
            for f in children["value"]:
                fid = f["id"]
                perms = get_permissions(drive_id, fid, token)
                role_info = extract_roles(perms)

                items.append({
                    "id": fid,
                    "name": f["name"],
                    "type": "folder" if "folder" in f else "file",
                    "drive_id": drive_id,
                    **role_info
                })

            return {"drive_id": drive_id, "items": items}

        # ------------------ CASE: SharePoint site navigation URL ------------------
        parsed = urlparse(folder_path)
        hostname = parsed.hostname

        if not hostname:
            raise HTTPException(400, detail="Invalid SharePoint URL")

        site = resolve_site_by_hostname(hostname, token)
        site_id = site["id"]

        path_after_hostname = parsed.path.split("/r/")[-1]
        parts = path_after_hostname.split("/")

        if "Shared Documents" not in parts:
            raise HTTPException(400, detail="Unable to extract SharePoint document path")

        idx = parts.index("Shared Documents")
        doc_path = "/".join(parts[idx:])

        api = f"{GRAPH_BASE}/sites/{site_id}/drive/root:/{doc_path}:/children"
        files = graph_get(api, token)

        items = []
        for f in files["value"]:
            fid = f["id"]
            drive_id = f["parentReference"]["driveId"]

            perms = get_permissions(drive_id, fid, token)
            role_info = extract_roles(perms)

            items.append({
                "id": fid,
                "name": f["name"],
                "type": "folder" if "folder" in f else "file",
                "drive_id": drive_id,
                **role_info
            })

        return {"drive_id": site_id, "items": items}

    # ------------------ CASE 2: NORMAL ONEDRIVE PATH ------------------
    clean = urllib.parse.unquote(folder_path)
    api = (
        f"{GRAPH_BASE}/me/drive/root:/{clean}:/children"
        if clean else
        f"{GRAPH_BASE}/me/drive/root/children"
    )

    files = graph_get(api, token)
    drive = graph_get(f"{GRAPH_BASE}/me/drive", token)

    items = []
    for f in files["value"]:
        fid = f["id"]

        perms = get_permissions(drive["id"], fid, token)
        role_info = extract_roles(perms)

        items.append({
            "id": fid,
            "name": f["name"],
            "type": "folder" if "folder" in f else "file",
            "drive_id": drive["id"],
            **role_info
        })

    return {
        "drive_id": drive["id"],
        "items": items
    }
