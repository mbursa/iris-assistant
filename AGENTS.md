# Code documentation rules

These rules apply to every Python file in this repository, especially `src/` and
the root entry points. Follow them whenever adding or modifying code.

## Declaration documentation

- Document every declaration with `#` line comments: modules, classes, protocols
  or interfaces, constants, class and instance properties, variables, standalone
  functions, nested functions, methods, and callback functions.
- Do not use triple-quoted docstrings as declaration documentation. Use only `#`
  comments so documentation has one consistent format.
- For declarations with a body, put the documentation immediately inside the
  body, directly after the declaration and before any executable statement.
- For declarations without a body, put the documentation immediately above the
  declaration.
- For variable, constant, and property assignments, put the documentation
  immediately above the assignment. Document the value's purpose, unit, valid
  range, ownership, or lifecycle where applicable.
- Keep the first line a concise purpose statement. Use `# --------------------------------------------------------------------------`
  separator lines before and after longer documentation blocks. Follow with
  descriptive paragraphs and relevant PHPDoc-style tags in line-comment form:
  `@param`, `@return`, `@throws`, `@type`, and `@var`.
- Include every parameter in `@param` tags when the declaration has parameters.
  Include `@return` for a non-`None` result and `@throws` for deliberate or
  meaningful errors callers need to handle. Describe thread-safety, ownership,
  blocking behavior, and external side effects when relevant.

Example for a function with a body:

```python
def start_microphone(
    audio_q: "queue.Queue[bytes]",
    stop_evt: threading.Event,
    settings: Settings,
) -> sd.InputStream:
    # Starts the configured microphone stream and queues PCM audio frames.
    # --------------------------------------------------------------------------
    # The callback must never block because it runs on PortAudio's audio thread.
    # @param audio_q: Bounded queue that receives PCM S16LE frame bytes.
    # @param stop_evt: Shared event that requests capture shutdown.
    # @param settings: Validated application audio settings.
    # @return: Started SoundDevice input stream owned by the caller.
    # @throws PortAudioError: If the selected input device cannot be opened.
    # --------------------------------------------------------------------------
    ...
#end def
```

Example for a constant, variable, or property:

```python
# Soniox's current real-time STT model identifier used by new sessions.
# @var str
DEFAULT_MODEL = "stt-rt-v5"
```

## Comments inside function and method bodies

- Add short `#` comments immediately before every meaningful logical block.
- Start block comments with lower-case text. Explain the block's intent,
  constraint, or invariant; do not narrate obvious syntax.
- Keep comments close to the code they govern. Update or remove a comment when
  the surrounding behavior changes.
- Use comments to make concurrency, queue overflow, shutdown, error handling,
  configuration precedence, token finalization, and UI-thread constraints
  explicit. These are important implementation concerns in this project.

Good:

```python
# drop overflowing frames so the audio callback never blocks or overruns.
try:
    audio_q.put_nowait(frame)
except queue.Full:
    pass
```

Avoid:

```python
# Put the frame into the queue.
audio_q.put_nowait(frame)
```

## Existing style

- Preserve the existing `#end def`, `#end class`, `#end if`, `#end for`, and
  related closing markers when editing a block that already uses them.
- Apply these documentation rules to all new declarations and to declarations
  touched during an edit. Do not make unrelated behavior changes solely to add
  comments.
