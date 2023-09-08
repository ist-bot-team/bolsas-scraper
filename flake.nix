{
  description = "Description for the project";

  inputs = {
    nixpkgs.url = "flake:nixpkgs";
    devenv.url = "github:cachix/devenv";
  };

  outputs = inputs@{ flake-parts, ... }:
    flake-parts.lib.mkFlake { inherit inputs; } {
      imports = [
        # To import a flake module
        # 1. Add foo to inputs
        # 2. Add foo as a parameter to the outputs function
        # 3. Add here: foo.flakeModule
        inputs.devenv.flakeModule

      ];
      systems = [ "x86_64-linux" "aarch64-linux" "aarch64-darwin" "x86_64-darwin" ];
      perSystem = { config, self', inputs', pkgs, system, ... }:
        let
          python = pkgs.python3;
        in
        {
          # Per-system attributes can be defined here. The self' and inputs'
          # module parameters provide easy access to attributes of the same
          # system.

          # Equivalent to  inputs'.nixpkgs.legacyPackages.hello;
          packages.default =
            let
              python = pkgs.python3;
            in
            python.pkgs.buildPythonApplication {
              name = "bolsas-scraper";

              propagatedBuildInputs = with python.pkgs;  [ requests wget beautifulsoup4 lxml ];

              src = ./.;
            };

          devenv.shells.default = {
            languages.python = {
              enable = true;
              package =  (pkgs.python3.withPackages (ps: with ps; with pkgs.python3Packages; [
                  requests
                  wget
                  lxml
                  beautifulsoup4
            ]));
            };
            dotenv.enable = true;
          };
        };
      flake = {
        # The usual flake attributes can be defined here, including system-
        # agnostic ones like nixosModule and system-enumerating ones, although
        # those are more easily expressed in perSystem.

      };
    };
}
