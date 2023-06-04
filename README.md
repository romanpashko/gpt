# GPT Engineer
**Specify what you want it to build, the AI asks for clarification, and then builds it.**

The entire codebase is generated. 

GPT Engineer is made to be easy to adapt, extend, and make your agent learn how you want your code to look.

## Project philosophy
- Simple to get value
- Flexible and easy to add new own "AI steps". See `steps.py`.
- Incrementally build towards a user experience of:
  1. high level prompting
  2. giving feedback to the AI that it will remember over time
- Fast handovers back and forth between AI and human
- Simplicity, all computation is "resumable" and persisted to the filesystem


## Usage

**Install**:

- `pip install -r requirements.txt`

**Run**:
- Create a new empty folder with a `main_prompt` file (or copy the example folder `cp example -r my-new-project`)
- Fill in the `main_prompt` in your new folder
- run `python main.py my-new-project`

**Results**:
- Check the generated files in my-new-project/workspace_clarified

## Features
You can specify the "identity" of the AI agent by editing the files in the `identity` folder.

Editing the identity, and evolving the main_prompt, is currently how you make the agent remember things between projects.

Each step in steps.py will have its communication history with GPT4 stored in the logs folder, and can be rerun with scripts/rerun_edited_message_logs.py.
