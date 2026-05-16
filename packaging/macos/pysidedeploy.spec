[app]
title = P2P Tetris
project_dir = ../..
input_file = src/p2p_tetris/client/app.py
exec_directory = build/pyside6-deploy/macos
project_file = 
icon = packaging/macos/P2P-Tetris.icns

[python]
python_path = 
packages = Nuitka==4.0

[qt]
qml_files = 
excluded_qml_plugins = 
modules = Core,Gui,Widgets
plugins = platforminputcontexts

[nuitka]
macos.permissions = NSLocalNetworkUsageDescription:Connect to a P2P Tetris server on your local network.
mode = standalone
extra_args = --quiet --noinclude-qt-translations --macos-target-arch=arm64 --macos-app-name="P2P Tetris" --macos-signed-app-name=com.ryansuc.p2p-tetris --macos-app-version=0.1.0 --macos-sign-identity=ad-hoc --product-name="P2P Tetris" --product-version=0.1.0 --file-version=0.1.0 --company-name=ryansuc --copyright="Copyright 2026 Ryan Suc"
