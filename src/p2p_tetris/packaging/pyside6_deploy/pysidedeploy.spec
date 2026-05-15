[app]
title = P2P Tetris
input_file = ../../../client/app.py
project_dir = ../../../..
exec_directory = build/pyside6-deploy

[python]
packages = p2p_tetris

[qt]
qml_files =
excluded_qml_plugins =

[nuitka]
extra_args = --follow-imports
