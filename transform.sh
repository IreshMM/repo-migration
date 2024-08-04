#!/bin/bash

yq '[.[] | {"name": .name, "target_name": .name | downcase() | sub("_", "-") | sub("sb-", ""), "url": .url }]' \
  source.yaml > target.yaml