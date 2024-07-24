from beet import Context, Container, JsonFile, Cache
from beet.contrib.vanilla import Vanilla
import subprocess
import os
import json
from pydantic import BaseModel
from typing import Any, TypeVar, Optional, Protocol
from pathlib import Path
from dataclasses import dataclass
from copy import deepcopy

V = TypeVar("V")


class MinecraftContainer(Container[str, V]):
    def normalize_key(self, key: str) -> str:
        return key if ":" in key else f"minecraft:{key}"


class Data(Protocol):
    _data: Any


class BlockState(BaseModel):
    default: Optional[bool] = None
    id: int
    properties: Optional[dict[str, str]] = None


class Block(BaseModel):
    definition: dict[str, Any]
    properties: Optional[dict[str, list[str]]] = None
    states: list[BlockState]


class Blocks(MinecraftContainer[Block], Data):
    def __init__(self, data: dict):
        self._data = deepcopy(data)
        super().__init__()
        for key, value in data.items():
            try:
                self[key] = Block(**value)
            except Exception as e:
                print(key, value)


class AbstractJsonFile(JsonFile, Data):
    def __init__(self, *args, data: dict, **kwargs):
        self._data = deepcopy(data)
        super().__init__(data, *args, **kwargs)


class Components(MinecraftContainer[Any]):
    def __init__(self, data: dict):
        super().__init__()
        for key, value in data.items():
            self[key] = value


class Items(MinecraftContainer[Components], Data):
    def __init__(self, data: dict):
        self._data = deepcopy(data)
        super().__init__()
        for key, value in data.items():
            self[key] = Components(value.get("components", {}))


class Packet(BaseModel):
    clientbound: set[str]
    serverbound: set[str]


class Packets(MinecraftContainer[Packet], Data):
    def __init__(self, data: dict):
        super().__init__()
        self._data = deepcopy(data)
        for key, value in data.items():
            self[key] = Packet(
                clientbound=set(value.get("clientbound", {}).keys()),
                serverbound=set(value.get("serverbound", {}).keys()),
            )


class Registries(MinecraftContainer[set[str]], Data):
    def __init__(self, data: dict):
        super().__init__()
        self._data = deepcopy(data)
        for key, value in data.items():
            self[key] = set(value["entries"].keys())


@dataclass
class Files:
    registries: Registries
    packets: Packets
    items: Items
    commands: AbstractJsonFile
    blocks: Blocks
    minecraft_nether: AbstractJsonFile
    minecraft_overworld: AbstractJsonFile


class GeneratedData:
    ctx: Context
    cache: Cache
    save_path: Path
    reports: Path
    minecraft_version: str

    files: Files = None # type: ignore

    def __init__(self, ctx: Context):
        self.ctx = ctx
        self.vanilla = ctx.inject(Vanilla)
        self.cache = ctx.cache["vanilla_registries"]
        self.save_path = self.cache.directory / "generated"
        self.reports = self.save_path / "generated" / "reports"
        self.minecraft_version = self.vanilla.minecraft_version

    def regen(self):
        release = self.vanilla.releases[self.minecraft_version]
        jar = release.cache.download(release.info.data["downloads"]["server"]["url"])
        os.makedirs(self.save_path, exist_ok=True)
        args = [
            "java",
            "-DbundlerMainClass=net.minecraft.data.Main",
            "-jar",
            jar,
            "--reports",
        ]

        subprocess.run(args, cwd=self.save_path, check=True)

    def refresh(self):
        with open(self.reports / "registries.json") as f:
            registries = Registries(json.load(f))
        with open(self.reports / "packets.json") as f:
            packets = Packets(json.load(f))
        with open(self.reports / "items.json") as f:
            items = Items(json.load(f))
        with open(self.reports / "commands.json") as f:
            commands = AbstractJsonFile(data=json.load(f))
        with open(self.reports / "blocks.json") as f:
            blocks = Blocks(json.load(f))
        biome_parameters = self.reports / "biome_parameters" / "minecraft"
        with open(biome_parameters / "nether.json") as f:
            minecraft_nether = AbstractJsonFile(data=json.load(f))
        with open(biome_parameters / "overworld.json") as f:
            minecraft_overworld = AbstractJsonFile(data=json.load(f))
        self.files = Files(
            registries=registries,
            packets=packets,
            items=items,
            commands=commands,
            blocks=blocks,
            minecraft_nether=minecraft_nether,
            minecraft_overworld=minecraft_overworld,
        )

    def ensure(self):
        if self.cache.json.get("minecraft_version") != self.minecraft_version:
            self.regen()
            self.cache.json["minecraft_version"] = self.minecraft_version
        if self.files is None:
            self.refresh()

    @property
    def registries(self) -> Registries:
        self.ensure()
        return self.files.registries

    @property
    def packets(self) -> Packets:
        self.ensure()
        return self.files.packets

    @property
    def items(self) -> Items:
        self.ensure()
        return self.files.items

    @property
    def commands(self) -> AbstractJsonFile:
        self.ensure()
        return self.files.commands

    @property
    def blocks(self) -> Blocks:
        self.ensure()
        return self.files.blocks

    @property
    def minecraft_nether(self) -> AbstractJsonFile:
        self.ensure()
        return self.files.minecraft_nether

    @property
    def minecraft_overworld(self) -> AbstractJsonFile:
        self.ensure()
        return self.files.minecraft_overworld
