{
  description = "Description for the project";

  inputs = {
    nixpkgs.url = "flake:nixpkgs";
    flake-parts = {
      url = "github:hercules-ci/flake-parts";
      inputs.nixpkgs-lib.follows = "nixpkgs";
    };
  };

  outputs = inputs@{ flake-parts, ... }:
    flake-parts.lib.mkFlake { inherit inputs; } {
      imports = [
        # To import a flake module
        # 1. Add foo to inputs
        # 2. Add foo as a parameter to the outputs function
        # 3. Add here: foo.flakeModule

      ];
      systems = [ "x86_64-linux" "aarch64-linux" "aarch64-darwin" "x86_64-darwin" ];
      # perSystem = { config, self', inputs', pkgs, system, ... }:
      perSystem = { pkgs, ... }:
        let
          python = pkgs.python3;
        in
        {
          # Per-system attributes can be defined here. The self' and inputs'
          # module parameters provide easy access to attributes of the same
          # system.

          # Equivalent to  inputs'.nixpkgs.legacyPackages.hello;
          packages.default =
            python.pkgs.buildPythonApplication {
              name = "bolsas-scraper";

              propagatedBuildInputs = with python.pkgs;  [ requests wget beautifulsoup4 lxml ];

              src = ./.;
            };

          devShells.default = pkgs.mkShell {
            packages = with pkgs; [

              (python.withPackages (ps: with ps; with python.pkgs; [
                requests
                wget
                lxml
                beautifulsoup4
              ]))
            ];
          };
        };
      flake = {
        # The usual flake attributes can be defined here, including system-
        # agnostic ones like nixosModule and system-enumerating ones, although
        # those are more easily expressed in perSystem.

      };
    };
}
