#!/usr/bin/env bash

aws lambda update-function-code --function-name metal-archives-ego-graph --zip-file fileb://lambda_function.zip
