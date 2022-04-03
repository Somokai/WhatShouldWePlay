# Merging

This file the steps the developer should take before submitting a PR.

## Test the code

## Run the spellchecker

If not installed, install cspell.

```cmd
npm install -g cspell
```

Run cspell from the base of this repo.

```cmd
cspell -c .cspell.json "**/*.py" "**/*.md"
```

## Run the markdown linter

Did you make an update to a .md file? if so, you'll need to do this.

If not installed, install markdownlint-cli

```cmd
npm install -g markdownlint-cli
```

Run markdownlint from the base of this repo.

```cmd
markdownlint <file>
```

## Run flake8 for python style guide enforcement

Run flake8 from the base of this repo. VSCode can automatically format by using
alt+shift+f.

```cmd
flake8 .
```
