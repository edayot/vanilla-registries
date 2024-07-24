
from beet import Context
from beet.contrib.vanilla import Vanilla, Release
import subprocess
from pathlib import Path
import os

def get_server_url(release: Release) -> Path:
    return release.cache.download(release.info.data["downloads"]["server"]["url"])



def beet_default(ctx: Context):
    vanilla = ctx.inject(Vanilla)
    release = vanilla.releases[vanilla.minecraft_version]
    jar = get_server_url(release)
    save_path = ctx.cache["vanilla_registries"].directory / "generated"
    os.makedirs(save_path, exist_ok=True)
    
    args = ["java", "-DbundlerMainClass=net.minecraft.data.Main", "-jar", jar, "--reports"]

    subprocess.run(args, cwd=save_path, check=True)

    reports = save_path / "generated" / "reports"


