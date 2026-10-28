{
  description = "Girasol - lossless photo/video rotation triage tool";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
  };

  outputs = { self, nixpkgs }:
    let
      systems = [ "x86_64-linux" "aarch64-linux" ];
      forAllSystems = nixpkgs.lib.genAttrs systems;
    in
    {
      packages = forAllSystems (system:
        let
          pkgs = nixpkgs.legacyPackages.${system};
          pythonEnv = pkgs.python3.withPackages (ps: [
            ps.pygobject3
            ps.pillow
            ps.pillow-heif
            ps.pytest
          ]);
          runtimeDeps = [
            pkgs.ffmpeg-full
            pkgs.libjpeg.bin
            pkgs.exiftool
            pkgs.libheif.bin
          ];
          giTypelibPath = pkgs.lib.makeSearchPath "lib/girepository-1.0" [
            pkgs.gtk4
            pkgs.libadwaita
            pkgs.gdk-pixbuf
            pkgs.glib.out
            pkgs.pango.out
            pkgs.harfbuzz
            pkgs.graphene
            pkgs.gobject-introspection
            pkgs.cairo
            pkgs.gsettings-desktop-schemas
          ];
        in
        {
          default = pkgs.stdenvNoCC.mkDerivation {
            pname = "girasol";
            version = "0.1.0";
            src = ./.;

            nativeBuildInputs = [ pkgs.makeWrapper pkgs.wrapGAppsHook4 ];
            buildInputs = [ pkgs.gtk4 pkgs.libadwaita ];

            dontBuild = true;

            installPhase = ''
              runHook preInstall

              mkdir -p $out/share/girasol
              cp -r ${./src}/girasol $out/share/girasol/girasol

              install -Dm644 ${./data/org.girasol.Girasol.desktop} \
                $out/share/applications/org.girasol.Girasol.desktop
              install -Dm644 ${./data/icons/org.girasol.Girasol.svg} \
                $out/share/icons/hicolor/scalable/apps/org.girasol.Girasol.svg

              makeWrapper ${pythonEnv}/bin/python3 $out/bin/girasol \
                --add-flags "-m girasol.main" \
                --prefix PYTHONPATH : "$out/share/girasol" \
                --prefix PATH : "${pkgs.lib.makeBinPath runtimeDeps}" \
                --prefix GI_TYPELIB_PATH : "${giTypelibPath}"

              runHook postInstall
            '';
          };
        });

      apps = forAllSystems (system: {
        default = {
          type = "app";
          program = "${self.packages.${system}.default}/bin/girasol";
        };
      });

      devShells = forAllSystems (system:
        let
          pkgs = nixpkgs.legacyPackages.${system};
          pythonEnv = pkgs.python3.withPackages (ps: [
            ps.pygobject3
            ps.pillow
            ps.pillow-heif
            ps.pytest
          ]);
          giTypelibPath = pkgs.lib.makeSearchPath "lib/girepository-1.0" [
            pkgs.gtk4
            pkgs.libadwaita
            pkgs.gdk-pixbuf
            pkgs.glib.out
            pkgs.pango.out
            pkgs.harfbuzz
            pkgs.graphene
            pkgs.gobject-introspection
            pkgs.cairo
            pkgs.gsettings-desktop-schemas
          ];
        in
        {
          default = pkgs.mkShell {
            packages = [
              pythonEnv
              pkgs.gtk4
              pkgs.libadwaita
              pkgs.gobject-introspection
              pkgs.ffmpeg-full
              pkgs.libjpeg.bin
              pkgs.exiftool
              pkgs.libheif.bin
              pkgs.xvfb-run
            ];

            shellHook = ''
              export GI_TYPELIB_PATH="${giTypelibPath}:$GI_TYPELIB_PATH"
              export PYTHONPATH="$PWD/src:$PYTHONPATH"
            '';
          };
        });
    };
}
