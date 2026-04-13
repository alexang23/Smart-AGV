# AGENTS.md (Agent Collaboration Guidelines)

This document defines the behavioral boundaries for AI Agents collaborating in this project, ensuring predictability in the development process.

## 1. Core Development Process: Plan First, Implement Later

- **Think First**: When involving cross-file or architectural changes, a "Modification Plan" must be produced first for developer review.

- **Minimal Changes**: Aim for "demonstrable and verifiable" goals. Avoid unnecessary large-scale refactoring.

- **Transparent Assumptions**: If environmental information is unclear, list your assumption points rather than making unsubstantiated guesses.

- **Inquiry and Confirmation**: When the AI Agent inquires or confirms matters with the developer, in addition to the Allow and Skip options, add an Other option, allowing the developer to input new execution steps and skip the original execution steps, so that the process can continue without interruption.

- **Git and GitHub Operations**: When performing git and GitHub operations, use git-commit and gh-cli skills.

## 2. Output Delivery Format

The output for each request should include the following sections:

- **Objective Description**: Briefly describe the problem you are solving.git

- **Change List**: List the affected relative paths and file names.

- **Verification Steps**: Provide verification methods after running `pipenv run python GYRO-500.py`. Verification steps should include:

  - Before conducting project tests, first check if the project's pipenv has the relevant packages installed. If not, the relevant packages must be installed before starting the tests.

  - The project must be executed and tested under the pipenv environment.

  - Command to start the application (e.g., `pipenv run python GYRO-500.py`).

  - Expected console output or log messages to confirm the application has started correctly.

  - If involving state changes, provide check steps.

  - Error Handling Verification: Test boundary scenarios, confirm the response complies with standards.

## 3. Security Boundaries

- **Prohibited Behaviors**: Do not modify global package versions (e.g., Python version) or delete protective scripts without discussion.

- **Scope Limitations**: This project focuses solely on the "SEMI E84 and WebAPI Communication Module"; please avoid introducing unrelated equipment control or database systems.
