# Neutron Sync CLI Client

## Introduction

Neutron Sync is a synchronization tool that helps you synchronize your small configuration files often referred to as dot files. Since these files are often sensitive and contain things such as encryption keys and passwords, files are encrypted before being stored remotely. Only you own the key that can decrypt the files. Additionally, if you use the default www.neutronsync.com remote store, then files are encrypted again at rest. Thus files are encrypted twice for extra security.

**Features:**

- Upload encrypted files to remote storage.
- Pull files that are missing or out sync.
- Push files that have changed.
- Multiple profile support: personal, work, etc
- Key exchange setup process on new machines

## Installation

```
pipx install nsync-cli
```

*pipx recommend but pip install also works*

## Usage

### One Time Setup

```
nsync login
nsync keygen
```

**!!!Note!!!** Be sure to keep `.config/nsync/config.json` safe. This file has your encryption key without it you can not decrypt your files.

### Everyday Usage

```
# Add new files to sync
nsync add path/to/file

# Pull files that need to be updated
nsync pull

# Add files to sync
# add command supports file globs like ".ssh/*" and "./ssh/**/*" with the second example being recursive.
nsync add "./ssh/**/*"

# Push updated files
nsync push
```

For more documentation see our [wiki](https://github.com/neutron-sync/nsync-cli/wiki).

## Key Exchange

To help speed up the setup of multiple machines, the CLI client supports a key exchange process.

See the [key exchange documentation](https://github.com/neutron-sync/nsync-cli/wiki/Key-Exchange) for more info.

## Limitation

- Files synced are assumed to be small configuration files. Larger files (>1mb) may choke or slow down sync processes.
- The client only supports a limit of 500 files to sync right now.

## Open Source

Visit our [Github](https://github.com/neutron-sync/nsync-cli) to contribute the project.

## Running Your Own Server

To use your own server update your config file, replace the `server_url` value: `"server_url": "https://www.neutronsync.com"`. Your config file is located at `~/.config/nsync/config.json`

See the [Neutron Server](https://github.com/neutron-sync/nsync-server) project for information on how to host your own server.
