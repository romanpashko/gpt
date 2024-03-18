"""
Entrypoint for the CLI tool.

This module serves as the entry point for a command-line interface (CLI) tool.
It is designed to interact with OpenAI's language models.
The module provides functionality to:
- Load necessary environment variables,
- Configure various parameters for the AI interaction,
- Manage the generation or improvement of code projects.

Main Functionality
------------------
- Load environment variables required for OpenAI API interaction.
- Parse user-specified parameters for project configuration and AI behavior.
- Facilitate interaction with AI models, databases, and archival processes.

Parameters
----------
None

Notes
-----
- The `OPENAI_API_KEY` must be set in the environment or provided in a `.env` file within the working directory.
- The default project path is `projects/example`.
- When using the `azure_endpoint` parameter, provide the Azure OpenAI service endpoint URL.
"""

import difflib
import logging
import os
import pdb
import sys

from pathlib import Path

import openai
import typer

from dotenv import load_dotenv
from termcolor import colored

from gpt_engineer.applications.cli.cli_agent import CliAgent
from gpt_engineer.applications.cli.collect import collect_and_send_human_review
from gpt_engineer.applications.cli.file_selector import FileSelector
from gpt_engineer.core.ai import AI, ClipboardAI
from gpt_engineer.core.default.disk_execution_env import DiskExecutionEnv
from gpt_engineer.core.default.disk_memory import DiskMemory
from gpt_engineer.core.default.file_store import FileStore
from gpt_engineer.core.default.paths import PREPROMPTS_PATH, memory_path
from gpt_engineer.core.default.steps import (
    execute_entrypoint,
    gen_code,
    handle_improve_mode,
    improve_fn as improve_fn,
)
from gpt_engineer.core.files_dict import FilesDict
from gpt_engineer.core.git import stage_uncommitted_to_git
from gpt_engineer.core.preprompts_holder import PrepromptsHolder
from gpt_engineer.tools.custom_steps import clarified_gen, lite_gen, self_heal

app = typer.Typer()  # creates a CLI app


def load_env_if_needed():
    """
    Load environment variables if the OPENAI_API_KEY is not already set.

    This function checks if the OPENAI_API_KEY environment variable is set,
    and if not, it attempts to load it from a .env file in the current working
    directory. It then sets the openai.api_key for use in the application.
    """
    # We have all these checks for legacy reasons...
    if os.getenv("OPENAI_API_KEY") is None:
        load_dotenv()
    if os.getenv("OPENAI_API_KEY") is None:
        load_dotenv(dotenv_path=os.path.join(os.getcwd(), ".env"))
    openai.api_key = os.getenv("OPENAI_API_KEY")

    if os.getenv("ANTHROPIC_API_KEY") is None:
        load_dotenv()
    if os.getenv("ANTHROPIC_API_KEY") is None:
        load_dotenv(dotenv_path=os.path.join(os.getcwd(), ".env"))


def load_prompt(input_repo: DiskMemory, improve_mode):
    """
    Load or request a prompt from the user based on the mode.

    Parameters
    ----------
    input_repo : DiskMemory
        The disk memory object where prompts and other data are stored.
    improve_mode : bool
        Flag indicating whether the application is in improve mode.

    Returns
    -------
    str
        The loaded or inputted prompt.
    """
    if input_repo.get("prompt"):
        return input_repo.get("prompt")

    if not improve_mode:
        input_repo["prompt"] = input(
            "\nWhat application do you want gpt-engineer to generate?\n"
        )
    else:
        input_repo["prompt"] = input("\nHow do you want to improve the application?\n")

    print("Prompt saved.")
    print(
        "If you want to use a different prompt later "
        + colored(
            f"you need to remove/edit the file: {input_repo.path}/prompt",
            "red",
        )
    )

    return input_repo.get("prompt")


def get_preprompts_path(use_custom_preprompts: bool, input_path: Path) -> Path:
    """
    Get the path to the preprompts, using custom ones if specified.

    Parameters
    ----------
    use_custom_preprompts : bool
        Flag indicating whether to use custom preprompts.
    input_path : Path
        The path to the project directory.

    Returns
    -------
    Path
        The path to the directory containing the preprompts.
    """
    original_preprompts_path = PREPROMPTS_PATH
    if not use_custom_preprompts:
        return original_preprompts_path

    custom_preprompts_path = input_path / "preprompts"
    if not custom_preprompts_path.exists():
        custom_preprompts_path.mkdir()

    for file in original_preprompts_path.glob("*"):
        if not (custom_preprompts_path / file.name).exists():
            (custom_preprompts_path / file.name).write_text(file.read_text())
    return custom_preprompts_path


def compare(f1: FilesDict, f2: FilesDict):
    def colored_diff(s1, s2):
        lines1 = s1.splitlines()
        lines2 = s2.splitlines()

        diff = difflib.unified_diff(lines1, lines2, lineterm="")

        RED = "\033[38;5;202m"
        GREEN = "\033[92m"
        RESET = "\033[0m"

        colored_lines = []
        for line in diff:
            if line.startswith("+"):
                colored_lines.append(GREEN + line + RESET)
            elif line.startswith("-"):
                colored_lines.append(RED + line + RESET)
            else:
                colored_lines.append(line)

        return "\n".join(colored_lines)

    for file in sorted(set(f1) | set(f2)):
        print(f"Changes to {file}:")
        diff = colored_diff(f1.get(file, ""), f2.get(file, ""))
        print(diff)


def prompt_yesno() -> bool:
    TERM_CHOICES = colored("y", "green") + "/" + colored("n", "red") + " "
    while answer := input(TERM_CHOICES).strip().lower() not in ["y", "yes", "n", "no"]:
        print("Please respond with 'y' or 'n'")
    return answer in ["y", "yes"]


@app.command()
def main(
    project_path: str = typer.Argument(".", help="path"),
    model: str = typer.Argument("gpt-4-1106-preview", help="model id string"),
    temperature: float = typer.Option(
        0.1,
        "--temperature",
        "-t",
        help="Controls randomness: lower values for more focused, deterministic outputs",
    ),
    improve_mode: bool = typer.Option(
        False,
        "--improve",
        "-i",
        help="Improve an existing project by modifying the files.",
    ),
    lite_mode: bool = typer.Option(
        False,
        "--lite",
        "-l",
        help="Lite mode: run a generation using only the main prompt.",
    ),
    clarify_mode: bool = typer.Option(
        False,
        "--clarify",
        "-c",
        help="Clarify mode: have the AI discuss and clarify the specification before implementation.",
    ),
    self_heal_mode: bool = typer.Option(
        False,
        "--self-heal",
        "-sh",
        help="Self-heal mode: enable the AI to attempt to fix errors encountered during execution.",
    ),
    azure_endpoint: str = typer.Option(
        "",
        "--azure",
        "-a",
        help="""Endpoint for your Azure OpenAI Service (https://xx.openai.azure.com).
            In that case, the given model is the deployment name chosen in the Azure AI Studio.""",
    ),
    use_custom_preprompts: bool = typer.Option(
        False,
        "--use-custom-preprompts",
        help="""Use your project's custom preprompts instead of the default ones.
          Copies all original preprompts to the project's workspace if they don't exist there.""",
    ),
    llm_via_clipboard: bool = typer.Option(
        False,
        "--llm-via-clipboard",
        help="Use the clipboard to communicate with the AI.",
    ),
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Enable verbose logging for debugging."
    ),
    debug: bool = typer.Option(
        False, "--debug", "-d", help="Enable debug mode for debugging."
    ),
):
    """
    The main entry point for the CLI tool that generates or improves a project.

    This function sets up the CLI tool, loads environment variables, initializes
    the AI, and processes the user's request to generate or improve a project
    based on the provided arguments.

    Parameters
    ----------
    project_path : str
        The file path to the project directory.
    model : str
        The model ID string for the AI.
    temperature : float
        The temperature setting for the AI's responses.
    improve_mode : bool
        Flag indicating whether to improve an existing project.
    lite_mode : bool
        Flag indicating whether to run in lite mode.
    clarify_mode : bool
        Flag indicating whether to discuss specifications with AI before implementation.
    self_heal_mode : bool
        Flag indicating whether to enable self-healing mode.
    azure_endpoint : str
        The endpoint for Azure OpenAI services.
    use_custom_preprompts : bool
        Flag indicating whether to use custom preprompts.
    verbose : bool
        Flag indicating whether to enable verbose logging.

    Returns
    -------
    None
    """

    if debug:
        sys.excepthook = lambda *_: pdb.pm()

    # Validate arguments
    if improve_mode and (clarify_mode or lite_mode):
        typer.echo("Error: Clarify and lite mode are not compatible with improve mode.")
        raise typer.Exit(code=1)

    # Set up logging
    logging.basicConfig(level=logging.DEBUG if verbose else logging.INFO)

    load_env_if_needed()

    if llm_via_clipboard:
        ai = ClipboardAI()
    else:
        ai = AI(
            model_name=model,
            temperature=temperature,
            azure_endpoint=azure_endpoint,
        )

    path = Path(project_path)
    print("Running gpt-engineer in", path.absolute(), "\n")

    prompt = load_prompt(DiskMemory(path), improve_mode)

    # configure generation function
    if clarify_mode:
        code_gen_fn = clarified_gen
    elif lite_mode:
        code_gen_fn = lite_gen
    else:
        code_gen_fn = gen_code

    # configure execution function
    if self_heal_mode:
        execution_fn = self_heal
    else:
        execution_fn = execute_entrypoint

    preprompts_holder = PrepromptsHolder(
        get_preprompts_path(use_custom_preprompts, Path(project_path))
    )

    memory = DiskMemory(memory_path(project_path))
    memory.archive_logs()

    execution_env = DiskExecutionEnv()
    agent = CliAgent.with_default_config(
        memory,
        execution_env,
        ai=ai,
        code_gen_fn=code_gen_fn,
        improve_fn=improve_fn,
        process_code_fn=execution_fn,
        preprompts_holder=preprompts_holder,
    )

    files = FileStore(project_path)
    if improve_mode:
        files_dict_before = FileSelector(project_path).ask_for_files()
        files_dict = handle_improve_mode(prompt, agent, memory, files_dict_before)
        if not files_dict or files_dict_before == files_dict:
            print(
                f"No changes applied. Could you please upload the debug_log_file.txt in {memory.path} folder in a github issue?"
            )
        else:
            print("\nChanges to be made:")
            compare(files_dict_before, files_dict)

            print()
            print(colored("Do you want to apply these changes?", "light_green"))
            if not prompt_yesno():
                files_dict = files_dict_before

    else:
        files_dict = agent.init(prompt)
        # collect user feedback if user consents
        config = (code_gen_fn.__name__, execution_fn.__name__)
        collect_and_send_human_review(prompt, model, temperature, config, memory)

    stage_uncommitted_to_git(path, files_dict, improve_mode)

    files.push(files_dict)

    if ai.token_usage_log.is_openai_model():
        print("Total api cost: $ ", ai.token_usage_log.usage_cost())
    else:
        print("Total tokens used: ", ai.token_usage_log.total_tokens())


if __name__ == "__main__":
    app()
