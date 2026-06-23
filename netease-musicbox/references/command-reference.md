# Command Reference

Use `--json` for every command. Successful responses contain `{ok: true, data}`;
failures contain `{ok: false, error}`. Read only the fields needed for the task and
do not expose cookies, tokens, or unrelated local state.

## Search and playback

| Intent | Command |
| --- | --- |
| Search songs | `musicbox search "<keyword>" --type song --json` |
| Play a song | `musicbox play --id <song_id> --json` |
| Play a playlist | `musicbox play --playlist <playlist_id> --json` |
| Resume current queue | `musicbox play --json` |
| Pause / resume / stop playback | `musicbox pause|resume|stop --json` |
| Next / previous song | `musicbox next [n] --json` / `musicbox prev [n] --json` |
| Show current state | `musicbox status --json` |
| Show current lyrics | `musicbox lyrics --current --json` |
| Set volume | `musicbox volume <0-100|+n|-n> --json` |
| Seek | `musicbox seek <seconds|+n|-n> --json` |

After `play`, `next`, or `prev`, wait 1–2 seconds and then call `status`. Check
`data.state` (`playing`, `paused`, or `stopped`) rather than inferring playback
from the original command's response.

If playback stops because of copyright restrictions, do not retry the same track;
tell the user and offer to select another result.

## Queue and mode

| Intent | Command |
| --- | --- |
| List queue | `musicbox queue list --json` |
| Append songs | `musicbox queue add <song_id>... --json` |
| Play queue item | `musicbox queue play <index> --json` |
| Clear queue | `musicbox queue clear --yes --json` |
| Set mode | `musicbox mode <ordered|ordered-loop|single-loop|random|random-loop> --json` |

`queue clear` removes the current queue. Show the user that effect and obtain
explicit confirmation immediately before adding `--yes`.

## Ending a listening session

If the user is done listening, wants to close MusicBox, or asks to stop listening,
run these commands in order:

```bash
musicbox stop --json
musicbox daemon stop --json
musicbox daemon status --json
```

Confirm that the final daemon status reports it is not running. Do not run this
sequence for a simple pause request.

## Daemon control

| Intent | Command |
| --- | --- |
| Start daemon | `musicbox daemon start --json` |
| Stop daemon | `musicbox daemon stop --json` |
| Inspect daemon | `musicbox daemon status --json` |
| Restart daemon | `musicbox daemon restart --json` |

The daemon is a persistent local process. It normally starts automatically for
control commands and continues after a track ends. The daemon and MusicBox's
interactive curses TUI are mutually exclusive; ask the user to close the TUI if it
is already running.

## Login

| Intent | Command |
| --- | --- |
| Check login state | `musicbox auth status --json` |
| Start QR login | `musicbox auth login --no-wait --json` |
| Check a completed QR login | `musicbox auth login --check <unikey> --json` |
| Log out | `musicbox auth logout --yes --json` |

`auth logout` removes local authentication state. Obtain explicit confirmation
immediately before adding `--yes`.

## Error handling

| Exit code | Meaning | Required handling |
| --- | --- | --- |
| 0 | Success | Continue normally. |
| 3 | Login required | Start the QR login split flow. |
| 4 | Daemon unavailable | Run `musicbox daemon start --json`, then retry once. |
| 5 | Unsupported operation | Read the error; seeking with `mpg123` is unsupported. |
| 10 | Confirmation required | Ask the user before retrying with `--yes`. |
