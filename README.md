# Neutron Sync CLI Client

## Introduction

Neutron Sync is a synchronization tool that helps you synchronize your small configuration files often referred to as dot files. Since these files are often sensitive and contain things such as encryption keys and passwords, the files are encrypted before storing them remotely. Only you own the key and can decrypt the files. Additionally, if you use the default www.neutronsync.com remote store, then files are encrypted again at rest. Thus files are encrypted twice for extra security.

## Installation

```
sudo -i
pip3 install nsync-cli
```

## Usage

### One Time Setup

```
nsync login
nsync keygen
```

**!!!Note!!!** Be sure to keep `.config/nsync/config.json` safe. This file has your encryption key without it you can not decrypt your files.

### Everyday Usage

Add new files to sync: `nsync add path/to/file`

Pull files that need to be updated: `nsync pull`

The `add` command supports file globs like `.ssh/*` and `./ssh/**/*` with the second example being recursive.
