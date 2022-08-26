{
  description = "Build a country imagemap";

  inputs.nixpkgs.url = "github:nixos/nixpkgs";
  inputs.gitignore = {
    url = "github:hercules-ci/gitignore.nix";
    inputs.nixpkgs.follows = "nixpkgs";
  };

  outputs = {
    self,
    nixpkgs,
    gitignore,
  }: let
    inherit (gitignore.lib) gitignoreSource;
    python-shp = system: let
      pkgs = nixpkgs.legacyPackages.${system};
      py-packages = python-packages: with python-packages; [pyshp];
    in
      pkgs.python3.withPackages py-packages;
    env = system: let
      pkgs = nixpkgs.legacyPackages.${system};
    in
      pkgs.mkShell {packages = [(python-shp system)];};
    website = system: let
      pkgs = nixpkgs.legacyPackages.${system};
    in
      pkgs.stdenv.mkDerivation {
        pname = "website";
        version = "0.0.0";
        src = gitignoreSource ./.;

        dontConfigure = true;

        buildInputs = [(python-shp system) pkgs.minify];

        postBuild = ''
          minify --recursive --sync --output minified/ .
        '';

        installPhase = ''
          runHook preInstall

          install -Dm644 -t"$out/src/" minified/src/*.{html,css} || true
          install -Dm644 -t"$out/src/photos/" minified/src/photos/*.{html,css} || true
          install -Dm644 -t"$out/assets/" minified/assets/*.{jpeg,png,pdf,svg} || true
          install -Dm644 -t"$out/assets/generated/" minified/assets/generated/*.{jpeg,png,pdf,svg} || true
          install -Dm644 -t"$out/assets/photos/" minified/assets/photos/*.{jpeg,png,pdf,svg} || true

          runHook postInstall
        '';
      };
  in {
    packages.aarch64-darwin.default = website "aarch64-darwin";
    packages.aarch64-linux.default = website "aarch64-linux";
    packages.i686-linux.default = website "i686-linux";
    packages.x86_64-darwin.default = website "x86_64-darwin";
    packages.x86_64-linux.default = website "x86_64-linux";

    devShells.aarch64-darwin.default = env "aarch64-darwin";
    devShells.aarch64-linux.default = env "aarch64-linux";
    devShells.i686-linux.default = env "i686-linux";
    devShells.x86_64-darwin.default = env "x86_64-darwin";
    devShells.x86_64-linux.default = env "x86_64-linux";
  };
}
