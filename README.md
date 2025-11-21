# MarkTec

Este Repositorio es para una pagina web de marketplace para ITM como proyecto para Taller de Investigacion ||

necesarios para correr:
tener creado el entorno virtual de python (.venv), en el mismo vscode o con el comando py -m venv .venv 
luego correr .venv\Scripts\activate

dependencias:

pip install flask
pip install mysql-connector-python
pip install python-dotenv
pip install werkzeug

cambios en "credenciales" del .env, checar el 'usuario' de conexion a mysql workbench:
SECRET_KEY=c24192ad91baa66b2d02a8e252cc570ffc57e5eeb7de02ecefeb54cb5a1922d0
MYSQL_HOST=localhost o 127.0.0.1 son los default, si no cambiar al propio
MYSQL_USER=root, si no el propio
MYSQL_PASSWORD=Root-MySQL_7903, la de cada uno
MYSQL_DB=marketec, todos corremos el mismo script asi que debe llamarse igual
MYSQL_PORT=3306, no cambia porque todos usamos workbench
EMAIL_USER=downbad7903@gmail.com, NO CAMBIAR
EMAIL_PASS=lbuzosknisvpygag, NO CAMBIAR