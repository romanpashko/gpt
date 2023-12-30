# Generated by CodiumAI

import gpt_engineer.applications.cli.main as main

from gpt_engineer.core.default.disk_execution_env import DiskExecutionEnv
from gpt_engineer.core.default.paths import ENTRYPOINT_FILE
from tests.caching_ai import CachingAI

main.AI = CachingAI


def simplified_main(path: str, mode: str = ""):
    model = "gpt-4-1106-preview"
    lite_mode = False
    clarify_mode = False
    improve_mode = False
    self_heal_mode = False
    azure_endpoint = ""
    verbose = False
    if mode == "lite":
        lite_mode = True
    elif mode == "clarify":
        clarify_mode = True
    elif mode == "improve":
        improve_mode = True
    elif mode == "self-heal":
        self_heal_mode = True
    main.main(
        path,
        model=model,
        lite_mode=lite_mode,
        clarify_mode=clarify_mode,
        improve_mode=improve_mode,
        self_heal_mode=self_heal_mode,
        azure_endpoint=azure_endpoint,
        use_custom_preprompts=False,
        verbose=verbose,
    )


def input_generator():
    yield "y"  # First response
    while True:
        yield "n"  # Subsequent responses


prompt_text = "Make a python program that writes 'hello' to a file called 'output.txt'"


class TestMain:
    #  Runs gpt-engineer with default settings and generates a project in the specified path.
    def test_default_settings_generate_project(self, tmp_path, monkeypatch):
        gen = input_generator()
        monkeypatch.setattr("builtins.input", lambda _: next(gen))
        p = tmp_path / "projects/example"
        p.mkdir(parents=True)
        (p / "prompt").write_text(prompt_text)
        simplified_main(str(p), "")
        ex_env = DiskExecutionEnv(path=p)
        ex_env.run(f"bash {ENTRYPOINT_FILE}")
        assert (p / "output.txt").exists()
        text = (p / "output.txt").read_text().strip()
        assert text == "hello"

    #  Runs gpt-engineer with improve mode and improves an existing project in the specified path.
    def test_improve_existing_project(self, tmp_path, monkeypatch):
        from pathlib import Path
        from typing import List

        import toml

        from gpt_engineer.core.default.disk_memory import DiskMemory
        from gpt_engineer.core.default.paths import metadata_path

        def mock_editor_file_selector(input_path: str, init: bool = True) -> List[str]:
            toml_file = (
                DiskMemory(metadata_path(input_path)).path / "file_selection.toml"
            )
            tree_dict = {"files": {"example_file.py": {"selected": True}}}

            with open(toml_file, "w") as f:
                toml.dump(tree_dict, f)

            return [str(Path(input_path) / "example_file.py")]

        monkeypatch.setattr(
            "gpt_engineer.applications.cli.file_selector.editor_file_selector",
            mock_editor_file_selector,
        )

        p = tmp_path / "projects/example"
        p.mkdir(parents=True)
        (p / "prompt").write_text(prompt_text)
        simplified_main(str(p), "improve")

        ex_env = DiskExecutionEnv(path=p)
        ex_env.run(f"bash {ENTRYPOINT_FILE}")
        assert (p / "output.txt").exists()
        text = (p / "output.txt").read_text().strip()
        assert text == "hello"

    #  Runs gpt-engineer with lite mode and generates a project with only the main prompt.
    def test_lite_mode_generate_project(self, tmp_path, monkeypatch):
        gen = input_generator()
        monkeypatch.setattr("builtins.input", lambda _: next(gen))
        p = tmp_path / "projects/example"
        p.mkdir(parents=True)
        (p / "prompt").write_text(prompt_text)
        simplified_main(str(p), "lite")
        ex_env = DiskExecutionEnv(path=p)
        ex_env.run(f"bash {ENTRYPOINT_FILE}")
        assert (p / "output.txt").exists()
        text = (p / "output.txt").read_text().strip()
        assert text == "hello"

    #  Runs gpt-engineer with clarify mode and generates a project after discussing the specification with the AI.
    def test_clarify_mode_generate_project(self, tmp_path, monkeypatch):
        gen = input_generator()
        monkeypatch.setattr("builtins.input", lambda _: next(gen))
        p = tmp_path / "projects/example"
        p.mkdir(parents=True)
        (p / "prompt").write_text(prompt_text)
        simplified_main(str(p), "clarify")
        ex_env = DiskExecutionEnv(path=p)
        ex_env.run(f"bash {ENTRYPOINT_FILE}")
        assert (p / "output.txt").exists()
        text = (p / "output.txt").read_text().strip()
        assert text == "hello"

    #  Runs gpt-engineer with self-heal mode and generates a project after discussing the specification with the AI and self-healing the code.
    def test_self_heal_mode_generate_project(self, tmp_path, monkeypatch):
        monkeypatch.setattr("builtins.input", lambda _: next(input_generator()))
        p = tmp_path / "projects/example"
        p.mkdir(parents=True)
        (p / "prompt").write_text(prompt_text)
        simplified_main(str(p), "self-heal")
        ex_env = DiskExecutionEnv(path=p)
        ex_env.run(f"bash {ENTRYPOINT_FILE}")
        assert (p / "output.txt").exists()
        text = (p / "output.txt").read_text().strip()
        assert text == "hello"
