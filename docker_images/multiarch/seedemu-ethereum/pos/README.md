# Instructions for building the multi-arch seedemu-ethereum:pos image

For users who want to build the seedemu-ethereum:pos image for multiple architectures, you can use the following instructions.

1. Firstly use CLI `docker buildx create --name multi-platform --use --platform linux/amd64,linux/arm64 --driver docker-container` to create a builder instance with multi-platform support.
2. Then use CLI `docker buildx build --platform linux/amd64,linux/arm64 -t handsonsecurity/seedemu-ethereum:pos .` to build the image for multiple architectures. Then the image will be built in your local cache. If you want to load the image into your local usage, you can use `--load` option.