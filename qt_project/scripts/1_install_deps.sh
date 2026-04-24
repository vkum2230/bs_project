#!/bin/bash
# 安装 Valhalla 编译依赖（树莓派）

echo "[Step 1] 更新 apt 源..."
sudo apt update

echo "[Step 1] 安装编译工具链..."
sudo apt install -y \
    build-essential cmake make ninja-build \
    git wget curl pkg-config

echo "[Step 1] 安装 C++ 库依赖..."
sudo apt install -y \
    libboost-all-dev \
    libcurl4-openssl-dev \
    libprotobuf-dev protobuf-compiler \
    liblz4-dev \
    libsqlite3-dev \
    zlib1g-dev \
    libgeos-dev libgeos++-dev \
    libspatialite-dev \
    libluajit-5.1-dev \
    python3-dev python3-pip

echo "[Step 1] 安装 osmium 工具（裁剪 OSM 数据用）..."
sudo apt install -y osmium-tool

echo "[Step 1] 完成！"
