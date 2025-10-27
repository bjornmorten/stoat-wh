# stoat-wh

Manage and send messages via [Stoat](https://stoat.chat) webhooks.

## Usage

```sh
stoat-wh <command> [options]
```

## Commands

| Command  | Description                      |
| -------- | -------------------------------- |
| `get`    | Fetch webhook information        |
| `edit`   | Edit webhook name                |
| `delete` | Delete a webhook                 |
| `send`   | Send a message through a webhook |

## Options

### Global

| Option       | Description                                    |
| ------------ | ---------------------------------------------- |
| `--debug`    | Show raw API responses and detailed error JSON |
| `-h, --help` | Show help message and exit                     |

### `get`

```sh
stoat-wh get <url> | <id> <token> [--json]
```

| Option   | Description                            |
| -------- | -------------------------------------- |
| `--json` | Output formatted JSON instead of plain |

### `edit`

```sh
stoat-wh edit <url> | <id> <token> [--name NAME]
```

| Option        | Description              |
| ------------- | ------------------------ |
| `--name NAME` | New name for the webhook |

### `delete`

```sh
stoat-wh delete <url> | <id> <token>
```

Deletes the specified webhook.

### `send`

```sh
stoat-wh send <url> | <id> <token> [options]
```

| Option                      | Description                                    |
| --------------------------- | -----------------------------------------------|
| `-c, --content TEXT`        | Message content (overridden by stdin if piped) |
| `--username NAME`           | Masquerade display name                        |
| `--avatar URL`              | Masquerade avatar URL                          |
| `--flags INT`               | Message flag bitfield                          |
| `--reply ID [ID ...]`       | Message IDs to reply to                        |
| `--embed PATH\|JSON [...]`  | Embed JSON string or file path                 |
| `--interactions PATH\|JSON` | Interactions JSON string or file path          |


## Environment

| Variable    | Description                                                                  |
| ----------- | ---------------------------------------------------------------------------- |
| `STOAT_API` | Override the Stoat API base URL (default: `https://stoat.chat/api/webhooks`) |

## Examples

### Get webhook info

```sh
stoat-wh get 01ABC TOKEN
```

### Edit webhook name

```sh
stoat-wh edit 01ABC TOKEN --name "New Webhook Name"
```

### Delete webhook

```sh
stoat-wh delete 01ABC TOKEN
```

### Send a simple message

```sh
stoat-wh send 01ABC TOKEN --content "Hello world!"
```

### Send message from stdin

```sh
echo "From stdin" | stoat-wh send 01ABC TOKEN
```

### Send with masquerade and embed

```sh
stoat-wh send 01ABC TOKEN --username "Bot" --avatar https://example.com/a.png \
  --embed '{"type": "Text", "title": "Hello", "description": "Embed message"}'
```

## License

MIT License © 2025 [bjornmorten](https://github.com/bjornmorten)
