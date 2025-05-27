# Contributing to DockFlare

First off, thank you for considering contributing to DockFlare! I appreciate your time and effort to help make this project better.

As a solo developer on this project, community contributions in various forms are incredibly valuable. This document provides some guidelines for contributing.

## How You Can Help

There are many ways you can contribute to DockFlare:

*   **Reporting Bugs:** If you find a bug, please **open an Issue** on GitHub. Provide detailed steps to reproduce it, what you expected to happen, what actually happened, and information about your setup (DockFlare version, OS, Docker version, etc.).
*   **Suggesting Enhancements & Ideas:** Have an idea for a new feature, an improvement, or a general question? Please **start a Discussion** on the GitHub repository's "Discussions" tab. This is a great place for broader conversations.
*   **Improving Documentation:** Clear documentation is key! If you see areas for improvement in the `README.md`, Wiki, or find parts of the setup confusing, your feedback (via Discussions or by improving it yourself via a PR) is welcome.
*   **Submitting Pull Requests:** If you'd like to contribute code, that's fantastic! Please follow the guidelines below. I recommend opening a Discussion or an Issue first to talk about significant changes.

## Getting Started (If You Plan to Code)

1.  **Fork the repository** on GitHub.
2.  **Clone your fork** locally: `git clone https://github.com/ChrispyBacon-dev/DockFlare.git`
3.  **Create a new branch** for your feature or bug fix: `git checkout -b feature/your-feature-name` or `git checkout -b fix/bug-description`.
4.  **Set up your development environment.** Ensure you have Python (matching the project version), Docker, Docker Compose, and Node.js/npm (for frontend assets) installed.
5.  **Install dependencies:**
    *   Python: `pip install -r requirements.txt` (preferably in a virtual environment)
    *   Node.js: `npm install` (in the `dockflare` subdirectory where `package.json` is located)

## Making Changes (For Pull Requests)

*   **Code Style:**
    *   Please follow [PEP 8](https://www.python.org/dev/peps/pep-0008/) guidelines for Python code.
    *   I aim for self-documenting code. Clear variable and function names are preferred over excessive inline comments.
    *   I use Black for formatting and Ruff/Flake8 for linting. Running these before committing is appreciated.
*   **Commit Messages:**
    *   Write clear and concise commit messages.
    *   Start with a capitalized, short (50 characters or less) summary.
    *   If necessary, add a blank line and then a more detailed explanatory text.
    *   Reference any relevant issue numbers (e.g., `Fixes #123`).
*   **Testing:**
    *   Please test your changes thoroughly. This includes manual testing of the affected functionality and, if possible, thinking about edge cases.
    *   Describe the testing you've done in your pull request description.
*   **Documentation:**
    *   If your changes affect user-facing functionality or configuration, please update the `README.md` or relevant Wiki pages.

## Submitting a Pull Request

1.  **Consider opening an Issue or starting a Discussion first**, especially for larger changes, so we can align on the approach.
2.  **Ensure your changes are well-tested.**
3.  **Update documentation** if necessary.
4.  **Push your changes** to your fork: `git push origin your-branch-name`.
5.  **Open a Pull Request** against the `unstable` branch of the main DockFlare repository. (Critical hotfixes for the `stable` branch might be considered, but `unstable` is the primary target for new development).
6.  **Provide a clear description** of your changes in the pull request:
    *   What problem does it solve or what feature does it add?
    *   How were the changes implemented?
    *   How did you test your changes?
    *   Reference any related Issues or Discussions.

## Community & Support

*   For **bug reports**, please use the [GitHub Issues](https://github.com/ChrispyBacon-dev/DockFlare/issues) tracker.
*   For **feature requests, questions, ideas, or general discussion**, please use the [GitHub Discussions](https://github.com/ChrispyBacon-dev/DockFlare/discussions) board.

I appreciate your interest and any contributions you make to help improve DockFlare!