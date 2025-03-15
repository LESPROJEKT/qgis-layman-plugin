class LaymanAPI:
    def __init__(self, base_url: str, api_prefix: str = "rest"):
        self.base_url = base_url.rstrip("/")
        self.api_prefix = api_prefix.strip("/")

    def _build_url(
        self, *parts: str, use_prefix: bool = True, query_params: dict = None
    ) -> str:
        url_parts = [self.base_url]
        if use_prefix:
            url_parts.append(self.api_prefix)
        url_parts.extend([p.strip("/") for p in parts])
        url = "/".join(url_parts)
        if query_params:
            query_string = "&".join(
                f"{k}={v}" for k, v in query_params.items() if v is not None
            )
            url = f"{url}?{query_string}"
        return url

    def get_roles_url(self) -> str:
        return self._build_url("roles")

    def get_users_url(self) -> str:
        return self._build_url("users")

    def get_workspaces_url(self) -> str:
        return self._build_url("workspaces")

    def get_workspace_url(self, layman_workspace: str) -> str:
        return self._build_url("workspaces", layman_workspace)

    def get_layers_url(self, layman_workspace: str) -> str:
        return self._build_url("workspaces", layman_workspace, "layers")

    def get_layer_url(self, layman_workspace: str, layer_name: str) -> str:
        return self._build_url("workspaces", layman_workspace, "layers", layer_name)

    def get_layer_thumbnail_url(self, layman_workspace: str, layer_name: str) -> str:
        return self._build_url(
            "workspaces", layman_workspace, "layers", layer_name, "thumbnail"
        )

    def get_map_thumbnail_url(self, layman_workspace: str, layer_name: str) -> str:
        return self._build_url(
            "workspaces", layman_workspace, "maps", layer_name, "thumbnail"
        )

    def get_layer_delete_url(self, layman_workspace: str, layer_name: str) -> str:
        return self._build_url("workspaces", layman_workspace, "layers", layer_name)

    def get_styles_url(self) -> str:
        return self._build_url("styles")

    def get_maps_url(self, layman_workspace: str, order_by: str = None) -> str:
        query_params = {"order_by": order_by} if order_by else None
        return self._build_url(
            "workspaces", layman_workspace, "maps", query_params=query_params
        )

    def get_map_url(self, layman_workspace: str, map_name: str) -> str:
        return self._build_url("workspaces", layman_workspace, "maps", map_name)

    def get_map_file_url(self, layman_workspace: str, map_name: str) -> str:
        return self._build_url("workspaces", layman_workspace, "maps", map_name, "file")

    def get_get_all_maps_url(self, order_by: str = None) -> str:
        return self._build_url(
            "maps",
            use_prefix=True,
            query_params={"order_by": order_by} if order_by else None,
        )

    def get_get_all_layers_url(self) -> str:
        return self._build_url("layers")

    def composition_file_url(self, composition_name: str) -> str:
        return self._build_url("maps", composition_name, "file")

    def get_layer_style_url(self, layman_workspace: str, layer_name: str) -> str:
        return self._build_url(
            "workspaces", layman_workspace, "layers", layer_name, "style"
        )

    def get_current_user_url(self) -> str:
        return self._build_url("current-user")

    def get_layer_chunk_url(self, layman_workspace: str, layer_name: str) -> str:
        return self._build_url(
            "workspaces", layman_workspace, "layers", layer_name, "chunk"
        )

    def get_user_delete_url(self, layman_username) -> str:
        return self._build_url("users", layman_username)
