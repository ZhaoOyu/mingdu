# Security

Please use GitHub's private vulnerability reporting on this repository for security issues once enabled. If it is unavailable, open an issue requesting a private contact without publishing exploit details or credentials.

Do not attach authentication tokens, unredacted device identifiers or personal configuration directories. Mingdu does not send telemetry or upload monitor data. Its normal runtime uses local operating-system APIs and local helper processes only.

Hardware commands must remain argument arrays, never shell-interpolated text. Do not bypass OS protections, install broad device permission rules, or run the GUI as administrator/root. Report any path that violates those guarantees.

Only the latest development version is maintained. There are no signed production binaries yet.
