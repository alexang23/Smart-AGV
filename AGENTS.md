# AGENTS.md (Agent Collaboration Guidelines)

This document defines the behavioral boundaries for AI Agents collaborating in this project, ensuring predictability in the development process.

## 1. Core Development Process: Plan First, Implement Later

- **Think First**: When involving cross-file or architectural changes, a "Modification Plan" must be produced first for developer review.

- **Minimal Changes**: Do not modify unrelated code solely for style, formatting, or refactoring unless explicitly requested. Avoid unnecessary large-scale refactoring.

- **Transparent Assumptions**: If environmental information is unclear, list your assumption points rather than making unsubstantiated guesses. Assumptions should be listed under an "Assumptions" section. If an assumption materially affects implementation, pause and request developer confirmation before proceeding.

- **Inquiry and Confirmation**: Whenever the AI asks for confirmation, should provide `Other` (developer specifies an alternative action, replacing the original proposed action) option, allowing the developer to input new execution steps and skip the original execution steps, so that the process can continue without interruption.

- **Git and GitHub Operations**: After successfully completing requested code changes, create a git commit unless:
  - the developer explicitly requests otherwise.
  - the repository is not under Git.
  - the implementation is intentionally incomplete.
  Commit messages must be clear, concise, and follow the Conventional Commits specification (e.g., feat(e84): ... or fix(agv): ...).

## 2. Output Delivery Format

The output for each request should include the following sections:

- **Objective Description**: Briefly describe the problem you are solving.

- **Modification Plan**:
  (if applicable)

- **Assumptions**:
  (if applicable)

- **Change List**: List the affected relative paths and file names.

- **Verification Steps**: When applicable, execute: `uv run python GYRO-500.py`
  If the requested change does not affect runtime behavior, explain why execution was unnecessary. Verification steps should include:

  - Before conducting project tests, first check if the project's uv has the relevant packages installed. Do not install unrelated packages.

  - The project must be executed and tested under the uv environment.

  If verification fails:
  - report the failure,
  - include logs or error messages,
  - do not claim success,
  - propose the next corrective step.

- **Verification Result**:
  (if applicable)

- **Git Commit**:
  feat(e84): ...

## 3. Security Boundaries

- **Prohibited Behaviors**: Do not modify:
  - Python version
  - build configuration

  unless explicitly approved.

- **Scope Limitations**: This project focuses solely on the "SEMI E84 AGV/AMR Module". New features should directly support:
  - SEMI E84
  - SEMI E87
  - SECS/GEM/HSMS
  - MQTT

  Do not introduce unrelated systems such as:
  - databases
  - PLC control
  - MES integration
  unless explicitly requested.

## 4. Additional References and Requirements

- SEMI SECS/GEM/HSMS message type and format reference: <http://www.hume.com/secs/>, <http://www.hume.com/secs/msgsPython.html>.
- MQTT <https://www.hivemq.com/mqtt/>, <https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html>
- aiomqtt <https://github.com/empicano/aiomqtt>
