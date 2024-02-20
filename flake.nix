{
  description = "Application packaged using poetry2nix";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/master";
    poetry2nix = {
      url = "github:nix-community/poetry2nix";
      inputs.nixpkgs.follows = "nixpkgs";
    };
  };

  outputs = { self, nixpkgs, poetry2nix }:
  let
    supportedSystems = [ "x86_64-linux" "aarch64-linux" ];
    forAllSystems = nixpkgs.lib.genAttrs supportedSystems;
    pkgs = forAllSystems (system: nixpkgs.legacyPackages.${system});
  in
  {
    packages = forAllSystems (system: let
      inherit (poetry2nix.lib.mkPoetry2Nix { pkgs = pkgs.${system}; }) mkPoetryApplication;
    in rec {
      argoneon = mkPoetryApplication {
        projectDir = self;
        postInstall = ''
          cp -r oled/ $out/oled/
          substituteInPlace $out/lib/python*/site-packages/argoneon/argoneonoled.py \
            --replace "/etc/argon/oled" "$out/oled"
        '';
      };
      default = argoneon;
    });

    devShells = forAllSystems (system: let
      inherit (poetry2nix.lib.mkPoetry2Nix { pkgs = pkgs.${system}; }) mkPoetryEnv;
    in {
      default = pkgs.${system}.mkShellNoCC {
        packages = with pkgs.${system}; [
          (mkPoetryEnv { projectDir = self; })
          poetry
        ];
      };
    });
    nixosModules = {
      default = self.outputs.nixosModules.argoneon;
      argoneon = { lib, pkgs, config, ... }:
      let
        system = config.nixpkgs.hostPlatform.system;
        moduleName = "argoneon";
        cfg = config."${moduleName}";
      in {
        options."${moduleName}" = with lib.types; with lib.options; {
          enable = mkEnableOption "Daemons (argoneond, argononed) and related settings for the Argon Eon raspberry-pi NAS case";
          i2c = mkOption {
            description = "Enable settings related to i2s (TODO: figure out why i2c is needed and which ones are needed)";
            type = bool;
            default = true;
          };
          user = mkOption {
            description = "user to run the services as";
            type = str;
            default = "root";
          };
          group = mkOption {
            description = "group to run the services as";
            type = str;
            default = "root";
          };
          temperature = mkOption {
            description = "C for Celsius, F for Farenheit";
            type = enum ["C" "F"];
            default = "C";
          };
          debug = mkOption {
            description = "enable debug config (corresponds to the `debug` option in the `[General]` section)";
            type = bool;
            apply = val: if val then "Y" else "N";
            default = false;
          };
          screenduration = mkOption {
            description = "how long each screen is visible";
            type = ints.unsigned;
            default = 30;
          };
          screensaver = mkOption {
            description = "???";
            type = ints.unsigned;
            default = 120;
          };
          oled = mkOption {
            description = "enable oled config (corresponds to the `enabled` option in the `[OLED]` section)";
            type = bool;
            apply = val: if val then "Y" else "N";
            default = true;
          };
          screenlist = mkOption {
            description = "list of screen items to display";
            type = listOf str;
            default = ["clock" "cpu" "storage" "bandwidth" "raid" "ram" "temp" "ip"];
            apply = scrList: lib.concatStringsSep " " scrList;
          };
          CPUFan = mkOption {
            description = "attrset of CPU temperatures (string-quoted float) to fan percentages";
            type = attrsOf ints.unsigned;
            default = {
              "55.0" = 30;
              "60.0" = 55;
              "65.0" = 100;
            };
          };
          HDDFan = mkOption {
            description = "attrset of HDD temperatures (string-quoted float) to fan percentages";
            type = attrsOf ints.unsigned;
            default = {
              "40.0" = 25;
              "44.0" = 30;
              "46.0" = 35;
              "48.0" = 40;
              "50.0" = 50;
              "52.0" = 55;
              "54.0" = 60;
              "60.0" = 100;
            };
          };
          power-button = mkEnableOption "Use the Argon ONE power button to shut down the machine";
        };

        config = let
          argoneonpkg = self.outputs.packages."${system}".argoneon;
          eonConf = {
            General = {
              inherit (cfg) temperature debug;
            };
            OLED = {
              inherit (cfg) screenduration screensaver screenlist;
              enabled = cfg.oled;
            };
            inherit (cfg) CPUFan HDDFan;
          };
          eonConfFile = builtins.toFile "argoneon.conf" (lib.generators.toINI {} eonConf);
        in
          with lib;
          with builtins;
            {


              environment.etc."argon/argoneon.conf".source = eonConfFile;


              boot.initrd.availableKernelModules = (optionals cfg.i2c ["i2c-bcm2835"]);
              # always load i2c-dev
              boot.initrd.kernelModules = (optionals cfg.i2c ["i2c-dev"]);

              hardware = mkIf cfg.i2c {
                # This adds the i2c group
                i2c.enable = true;
                # add deviceTree overlays for i2c buses
                raspberry-pi."4" = {
                  # bus 0 seems related to the vido processor: https://github.com/NixOS/nixos-hardware/blob/72d53d51704295f1645d20384cd13aecc182f624/raspberry-pi/4/i2c.nix#L26
                  # bus 1 seems related to a more general use?: https://github.com/NixOS/nixos-hardware/blob/72d53d51704295f1645d20384cd13aecc182f624/raspberry-pi/4/i2c.nix#L39
                  # for the powerbutton the i2c bus "1" is used, is the other one necessary?
                  i2c0.enable = false;
                  i2c1.enable = true;
                  pwm0.enable = true;
                };
                # Add the device tree overlay to expose the power button for the gpio-keys module
                deviceTree.overlays = [
                  (mkIf cfg.power-button {
                    name = "power-button";
                    dtsText = ''
                      /dts-v1/;
                      /plugin/;

                      / {
                          compatible = "raspberrypi,4-model-b";

                          fragment@0 {
                                  // Configure the gpio pin controller
                                  target = <&gpio>;
                                  __overlay__ {
                                          pin_state: button_pins@0 {
                                                  brcm,pins = <4>; // gpio number
                                                  brcm,function = <0>; // 0 = input, 1 = output
                                                  brcm,pull = <1>; // 0 = none, 1 = pull down, 2 = pull up
                                          };
                                  };
                          };
                          fragment@1 {
                                  target-path = "/";
                                  __overlay__ {
                                          button: button@0 {
                                                  compatible = "gpio-keys";
                                                  pinctrl-names = "default";
                                                  pinctrl-0 = <&pin_state>;
                                                  status = "okay";

                                                  key: key {
                                                          linux,code = <116>;
                                                          gpios = <&gpio 4 1>;
                                                          label = "KEY_POWER";
                                                  };
                                          };
                                  };
                          };

                          __overrides__ {
                                  gpio =        <&key>,"gpios:4",
                                                    <&button>,"reg:0",
                                                    <&pin_state>,"brcm,pins:0",
                                                    <&pin_state>,"reg:0";
                                  label =       <&key>,"label";
                                  keycode =     <&key>,"linux,code:0";
                                  gpio_pull =   <&pin_state>,"brcm,pull:0";
                                  active_high = <&key>,"gpios:4";
                          };

                      };
                    '';
                  })
                ];
              };


              systemd.targets."${moduleName}" = {
                wantedBy = ["multi-user.target"];
                after = ["multi-user.target"];
              };

              systemd.services."argoneond" = {
                after = ["${moduleName}.target"];
                bindsTo = ["${moduleName}.target"];
                path = with pkgs; [
                  smartmontools
                  i2c-tools
                ];
                # restart service if configuratin changes between generations
                restartTriggers = [eonConfFile];
                serviceConfig = {
                  SupplementaryGroups = mkIf cfg.i2c "i2c";
                  Type = "simple";
                  User = cfg.user;
                  Group = cfg.group;
                  ExecStart = "${argoneonpkg}/bin/argoneond SERVICE";
                  Restart = "always";
                };
              };

              systemd.services."argononed" = {
                after = ["${moduleName}.target"];
                bindsTo = ["${moduleName}.target"];
                path = with pkgs; [
                  smartmontools
                  zfs
                  mdadm
                  i2c-tools
                ];
                # restart service if configuratin changes between generations
                restartTriggers = [eonConfFile];
                serviceConfig = {
                  SupplementaryGroups = mkIf cfg.i2c "i2c";
                  Restart = "always";
                  User = cfg.user;
                  Group = cfg.group;
                  ExecStart = "${argoneonpkg}/bin/argononed SERVICE";
                  Type = "simple";
                  RemainAfterExit = "true";
                };
              };

              # Add a script to make the case power board turn off the power once
              # the Pi has shut down
              systemd.services.argonone-power-off = mkIf cfg.power-button {
                wantedBy = ["poweroff.target"];
                after = ["systemd-poweroff.service"];

                # TODO: what do these magic values do?
                # i2cset [-f] [-y] [-m MASK] [-r] [-a] I2CBUS CHIP-ADDRESS DATA-ADDRESS [VALUE] ... [MODE]
                # I2CBUS: 1
                # CHIP-ADDRESS: 0x01a
                # VALUE: 0xff
                script = "${pkgs.i2c-tools}/bin/i2cset -y 1 0x01a 0xff";

                unitConfig.DefaultDependencies = "no";

                serviceConfig = {
                  SupplementaryGroups = mkIf cfg.i2c "i2c";
                  Type = "oneshot";
                  User = cfg.user;
                  Group = cfg.group;
                  TimeoutStartSec = "0";
                };
              };

            };
          };
    };

  };
}
