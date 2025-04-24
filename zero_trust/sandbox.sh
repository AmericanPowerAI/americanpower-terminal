#!/bin/bash
# Isolates risky commands using Wasmer
CMD=$1
wasmer run --deny-write --deny-net /usr/bin/$CMD
