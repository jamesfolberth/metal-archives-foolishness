#!/usr/bin/env bash

zipfile='lambda_function.zip'

rm -f $zipfile
pushd venv/lib/python3.7/site-packages
zip -r9 ../../../../$zipfile .
popd
zip -g $zipfile metal_archives_ego_graph.py
zip -gj $zipfile ../graph_viz/make_ego2.py
