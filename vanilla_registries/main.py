
from beet import Context, Container
from beet.contrib.vanilla import Vanilla
import subprocess
import os
import json



class RegistryContainer(Container[str, set[str]]):
    def __init__(self, data: dict):
        super().__init__()
        for key, value in data.items():
            self[key] = set(value["entries"].keys())
        
    def normalize_key(self, key: str) -> str:
        return key if ":" in key else f"minecraft:{key}"


class GeneratedData:
    registries: RegistryContainer

    def __init__(self, ctx: Context):
        cache = ctx.cache["vanilla_registries"]
        save_path = cache.directory / "generated"
        reports = save_path / "generated" / "reports"

        if cache.json.get("generated", True):
            vanilla = ctx.inject(Vanilla)
            release = vanilla.releases[vanilla.minecraft_version]
            jar = release.cache.download(release.info.data["downloads"]["server"]["url"])
            os.makedirs(save_path, exist_ok=True)
            args = ["java", "-DbundlerMainClass=net.minecraft.data.Main", "-jar", jar, "--reports"]

            subprocess.run(args, cwd=save_path, check=True)
        cache.json["generated"] = False

        with open(reports / "registries.json") as f:
            self.registries = RegistryContainer(json.load(f))

