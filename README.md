Gen-Ed: Generative AI for Education
===================================

Gen-Ed is a framework for building web applications that use generative AI
(LLMs) for education (i.e., organized around instructors and their classes of
students for use in teaching and learning contexts).

The framework provides most of the common functionality any application of this
type might need, including:

- Authentication, including single-sign-on from Google, Github, and Microsoft.
- Class enrollment, with separate instructor and student roles.
- Connecting to LMSes via LTI (for automatic authentication and enrolling).
- Class management and data export.
- Admin interfaces.

The repository also contains two applications that are built on Gen-Ed:

1. **CodeHelp** [1,2]: A tool for assisting students in computer science
   classes without giving them solution code. <https://codehelp.app/>

2. **Starburst**: A topic-exploration tool for writing assignments.
   <https://strbrst.xyz/>

#### References

[1] [CodeHelp: Using Large Language Models with Guardrails for Scalable Support
in Programming Classes](https://arxiv.org/abs/2308.06921). Mark Liffiton, Brad
Sheese, Jaromir Savelka, and Paul Denny. 2023. In Proceedings of the 23rd Koli
Calling International Conference on Computing Education Research (Koli Calling
'23).  DOI: [10.1145/3631802.3631830](https://doi.org/10.1145/3631802.3631830)

[2] [Patterns of Student Help-Seeking When Using a Large Language Model-Powered
Programming Assistant](https://arxiv.org/abs/2310.16984). Brad Sheese, Mark
Liffiton, Jaromir Savelka, and Paul Denny. 2024. In Proceedings of the 26th
Australasian Computing Education Conference (ACE '24).  DOI:
[10.1145/3636243.3636249](https://doi.org/10.1145/3636243.3636249)


Install
-------

Requires Python 3.10 or higher.

1. Create and activate a Python virtual environment.
   (E.g., `python3 -m venv venv; source venv/bin/activate`)

2. Install the Gen-Ed package and bundled applications in 'editable' mode:

```sh
pip install -e .
```


Set Up an Application
---------------------

1. In the root of the repository, create `.env` and populate it with
   environment variables to configure the application.  See `.env.test` for a
   list of all available variables.  The required variables are:
   - `FLASK_INSTANCE_PATH`: Path to an instance folder for storing the DB,
     etc.  Commonly set to `instance` (Requires the folder to be already created).
   - `SECRET_KEY`: A secure random string used to sign session cookies.
   - `BASE_URL`: The base URL for API requests (e.g., "https://api.dartmouth.edu").
   - `JWT_URL`: The JWT token generation endpoint (e.g., "https://api.dartmouth.edu/api/jwt").
   - `DARTMOUTH_API_KEY`: Your Dartmouth API key for authentication.
   - `SYSTEM_MODEL`: API endpoint path for the default model (e.g., "/api/ai/tgi/codellama-13b-instruct-hf/generate").
     Full URL will be constructed as (BASE_URL)(SYSTEM_MODEL).
   - `DEFAULT_CLASS_MODEL_SHORTNAME`: Display name for the default model in new classes.
     `CodeLlama-13B` is the standard default.

*Optionally*, if you want to allow logins from 3rd party authentication
providers, set any of the following pairs with IDs/secrets obtained from
registering your application with the given provider:

```
GOOGLE_CLIENT_ID=[...]
GOOGLE_CLIENT_SECRET=[...]
GITHUB_CLIENT_ID=[...]
GITHUB_CLIENT_SECRET=[...]
MICROSOFT_CLIENT_ID=[...]
MICROSOFT_CLIENT_SECRET=[...]
```

Then, to set up an application (CodeHelp, for example):

2. Initialize database:

```sh
flask --app codehelp initdb
```

3. Apply custom dartmouth database migrations:

```sh
flask --app codehelp dartmouth-migrations
```

4. Create at least one admin user:

```sh
flask --app codehelp newuser --admin [username]
```

This will create and display a randomly-generated password.
To change the password:

```sh
flask --app codehelp setpassword [username]
```

5. (Optional) To serve files from `/.well-known` (for domain verification,
   etc.), place the files in a `.well-known` directory inside the Flask
   instance folder.


Running an Application
----------------------

For example, to run the CodeHelp app:

```sh
flask --app codehelp run

# or, during development:
flask --app codehelp --debug run
```

Dartmouth
-------------
See `DARTMOUTH.md` for details about all the modifications made to the base project and API specifications.

Running Tests
-------------

First, install test dependencies:

```sh
pip install -e .[test]
```

Run all tests:

```sh
pytest
```

For code coverage report:

```sh
pytest --cov=src/gened --cov=src/codehelp --cov-report=html && xdg-open htmlcov/index.html
```

For mypy type checking:

```sh
mypy
```


Developing
----------

See `DEVELOPING.md` for additional instructions and information for developing
an application and/or contributing to the project.


Author
------

Gen-Ed and the included applications are by Mark Liffiton. CodeHelp and Gen-Ed were subsequently modified by Rana Moeez Hassan. The modifications were made to utilize the AI Models API provided by Dartmouth College.


Licenses
--------

Gen-Ed and the included applications are licensed under the GNU Affero General
Public License version 3 (AGPL-3.0-only).

Brand icons from [Simple Icons](https://simpleicons.org/) are licensed under
CC0-1.0.  Other icons from [Lucide](https://lucide.dev/) are licensed under the
Lucide ISC license.

For the text of these licenses, see the LICENSES directory.
