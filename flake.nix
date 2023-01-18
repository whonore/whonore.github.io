{
  description = "Build my website";

  inputs.nixpkgs.url = "github:nixos/nixpkgs";
  inputs.flake-utils.url = "github:numtide/flake-utils";
  inputs.gitignore = {
    url = "github:hercules-ci/gitignore.nix";
    inputs.nixpkgs.follows = "nixpkgs";
  };

  outputs = {
    self,
    nixpkgs,
    flake-utils,
    gitignore,
  }:
    flake-utils.lib.eachDefaultSystem (system: let
      inherit (gitignore.lib) gitignoreSource;
      pkgs = nixpkgs.legacyPackages.${system};
      build-pkgs = {dev ? false}: let
        py-packages = python-packages:
          with python-packages;
            [pyshp]
            ++ (pkgs.lib.optionals dev [black flake8 isort mypy pathspec]);
        python = pkgs.python3.withPackages py-packages;
      in [python pkgs.imagemagick pkgs.jpegoptim pkgs.minify pkgs.postcss-cli pkgs.svgcleaner];

      env = pkgs.mkShell {packages = build-pkgs {dev = true;};};
      website = pkgs.stdenv.mkDerivation {
        pname = "website";
        version = "0.0.0";
        src = gitignoreSource ./.;

        dontConfigure = true;

        postPatch = "patchShebangs scripts";

        enableParallelBuilding = true;
        buildInputs = build-pkgs {};

        installFlags = ["INSTALL_DIR=${placeholder "out"}"];
      };
    in {
      packages.default = website;
      devShells.default = env;
    });
}
