{
  description = "AIE2026 exercises: Python 3.12 and uv";

  inputs.nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";

  outputs = { nixpkgs, ... }:
    let
      systems = [
        "x86_64-linux"
        "aarch64-linux"
        "x86_64-darwin"
        "aarch64-darwin"
      ];
      forAllSystems = nixpkgs.lib.genAttrs systems;
    in
    {
      devShells = forAllSystems (system:
        let
          pkgs = import nixpkgs { inherit system; };
        in
        {
          default = pkgs.mkShell {
            packages = with pkgs; [
              python312
              uv
              git
              gh
            ];

            # uv.lock の依存関係を使い、Pythonも講座指定版に固定する。
            UV_PYTHON = "${pkgs.python312}/bin/python3.12";
            UV_PYTHON_DOWNLOADS = "never";

            shellHook = ''
              echo "AIE2026: Python 3.12 / uv"
              echo "Run: uv sync --frozen"
            '';
          };
        });
    };
}
