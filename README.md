# FastAPI Nuxt4 template

## **Pre setup**

- [Install `Python 3.14`](https://www.python.org/), or use [pyenv](https://github.com/pyenv/pyenv) (python version mananger) to install python
- [Install `Node.js 24+`](https://nodejs.org/en), or use [nvm](https://github.com/nvm-sh/nvm) (node version manager) to install Node.js
- [Install `Docker`, `docker-compose`](https://docs.docker.com/get-docker/)
- Install `make` command. [Windows](https://stackoverflow.com/questions/32127524/how-to-install-and-use-make-in-windows), [Linux](https://askubuntu.com/questions/161104/how-do-i-install-make) and [Mac](https://stackoverflow.com/questions/10265742/how-to-install-make-and-gcc-on-a-mac)

## **Setup on Local**

1. Configure `.env` file.

    ```sh
    cp secret/.env.example secret/.env
    ```

2. Create python virtual environment.

    - [Install `uv`](https://docs.astral.sh/uv/getting-started/installation/),

    - Install python packages using `uv`. It will create virtual environment in `back/.venv`.

    ```sh
    cd back
    uv sync
    ```

3. pre-commit.

    - required to activate `.venv` virtual environment.

    ```sh
    cd back && source .venv/bin/activate
    pre-commit install
    ```

4. Install and start. See [Makefile](./Makefile) for more detailed commands.

    - enjoy

    ```sh
    make install
    ```

    - frontend: <http://localhost:3000>
    - backend: <http://localhost:8000/docs>

5. Seed users are listed in [users.json](./back/app/seeds/datas/users.json). Set `SEED_DEV_PASSWORD` in `secret/.env` before seeding to choose their password; otherwise a random one is generated and printed in the seeder log.

6. Linter and typecheck

    ```sh
    make lint
    ```

## **Install the packages**

1. Python (back)

    ```sh
    make bash-back
    uv add <package-name>
    ```

2. Nuxt (front)

    ```sh
    make bash-front
    pnpm install
    pnpm add <package-name>
    ```

3. Database (MongoDB) — full guide: [docs/DATABASE.md](docs/DATABASE.md)

    - The `mongo` service runs MongoDB locally; set `MONGO_URI` in `secret/.env` to use Atlas instead.
    - It runs as a single-node replica set (`rs0`): the booking saga and outbox need transactions and change streams.
      From your host machine connect with `mongodb://localhost:27018/?directConnection=true`.
    - `make seed` loads every collection in `data/mock/` (see its README), creates the login users
      (password from `SEED_DEV_PASSWORD`) and all indexes. Re-running it resets the mock collections.
    - There are no migrations: collections and indexes are defined in `back/app/db/mongo.py`.

4. Create python virtual environment in local project folder

    ```sh
    rm -rf .venv && cp back/uv.lock . && cp back/pyproject.toml . && cp back/.python-version . && uv sync && rm uv.lock pyproject.toml .python-version
    ```

5. Install node modules in local project folder

    ```sh
    rm -rf node_modules && cp front/.nvmrc . && cp front/package.json . && cp front/pnpm-lock.yaml . && cp front/pnpm-workspace.yaml . && source $(HOME)/.nvm/nvm.sh && nvm use && pnpm install && rm .nvmrc package.json pnpm-lock.yaml pnpm-workspace.yaml
    ```
