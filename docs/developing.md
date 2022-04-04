# Developing

This file explains how to initially setup this repo after cloning, along with
running.

## Initial Setup

1. Create a virtual environment to reduce cross-project issues.

    ```cmd
    py -m venv venv
    ```

2. Activate the virtual environment.

    ```cmd
    venv/scripts/activate
    ```

3. Install all dependencies.

    ```cmd
    pip install --upgrade -r pip-requirements.txt
    ```

4. Follow the guide at [https://www.freecodecamp.org/news/create-a-discord-bot-with-python/]
to create a discord bot application and generate a token for the bot to use.

5. Create a .env file and add the token to the file via ```TOKEN=<TOKEN>```

## Running

1. Activate the virtual environment.

    ```cmd
    venv/scripts/Activate
    ```

2. Run the Bot.

    ```cmd
    py src/main.py
    ```
