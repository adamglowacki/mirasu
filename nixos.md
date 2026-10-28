# Installing Mirasu permanently on NixOS

This makes the `mirasu` command available everywhere and adds an
"Mirasu" entry to the GNOME Activities overview / app search, so you
don't need to `cd` into this repo and run `nix run` by hand.

## home-manager

Add the package to `home.packages` in your `home.nix`:

```nix
home.packages = [
  (builtins.getFlake "/home/ai/mirasu").packages.${builtins.currentSystem}.default
];
```

Then apply it:

```
home-manager switch
```

## Plain NixOS (no home-manager)

Add the same package to `environment.systemPackages` in
`configuration.nix` instead:

```nix
environment.systemPackages = [
  (builtins.getFlake "/home/ai/mirasu").packages.${builtins.currentSystem}.default
];
```

Then rebuild:

```
sudo nixos-rebuild switch
```

## Using it

- From GNOME: open Activities, search "Mirasu", launch it — it opens
  a folder picker since no path was given on a desktop launch.
- From a terminal: `mirasu /path/to/photos` (add `--recursive` to
  include subdirectories) still works exactly as before.

## Caveat: the local path

`builtins.getFlake "/home/ai/mirasu"` pins the install to this exact
clone's path on disk. If you move or delete this directory, the
home-manager/NixOS config referencing it will fail to build.

Once this repo is pushed to a git remote, replace that line with a
pinned fetch instead, so the install no longer depends on the clone:

```nix
(builtins.getFlake "git+https://github.com/<you>/<repo>.git?ref=main").packages.${builtins.currentSystem}.default
```

or, using `builtins.fetchGit`:

```nix
(import (builtins.fetchGit {
  url = "https://github.com/<you>/<repo>.git";
  ref = "main";
}) ...)
```

`nix flake lock` / a flake input in your system flake is the more
idiomatic route if your NixOS config is itself a flake — it gives you
a reproducible, pinned revision in a lockfile rather than always
tracking the branch tip.
