#!/usr/bin/env bash

show_loading() {
  local i
  printf '\n'
  for i in {1..18}; do
    case $((i % 4)) in
      0) printf '\r\033[1;36m  Initializing TerminalGPT |\033[0m' ;;
      1) printf '\r\033[1;36m  Initializing TerminalGPT /\033[0m' ;;
      2) printf '\r\033[1;36m  Initializing TerminalGPT -\033[0m' ;;
      3) printf '\r\033[1;36m  Initializing TerminalGPT \\\033[0m' ;;
    esac
    sleep 0.055
  done
  printf '\r\033[1;36m  Initializing TerminalGPT [OK]\033[0m\n'
  printf '  Preparing installer...\n\n'
}

show_welcome() {
  local magenta=$'\033[1;35m' red=$'\033[1;31m' cyan=$'\033[1;36m' white=$'\033[1;97m' gray=$'\033[0;37m' reset=$'\033[0m'
  local T1='████████╗' T2='╚══██╔══╝' T3='   ██║   ' T4='   ██║   ' T5='   ██║   ' T6='   ╚═╝   '
  local E1='███████╗' E2='██╔════╝' E3='█████╗  ' E4='██╔══╝  ' E5='███████╗' E6='╚══════╝'
  local R1='██████╗ ' R2='██╔══██╗' R3='██████╔╝' R4='██╔══██╗' R5='██║  ██║' R6='╚═╝  ╚═╝'
  local M1='███╗   ███╗' M2='████╗ ████║' M3='██╔████╔██║' M4='██║╚██╔╝██║' M5='██║ ╚═╝ ██║' M6='╚═╝     ╚═╝'
  local I1='██╗' I2='██║' I3='██║' I4='██║' I5='██║' I6='╚═╝'
  local N1='███╗   ██╗' N2='████╗  ██║' N3='██╔██╗ ██║' N4='██║╚██╗██║' N5='██║ ╚████║' N6='╚═╝  ╚═══╝'
  local A1=' █████╗ ' A2='██╔══██╗' A3='███████║' A4='██╔══██║' A5='██║  ██║' A6='╚═╝  ╚═╝'
  local L1='██╗     ' L2='██║     ' L3='██║     ' L4='██║     ' L5='███████╗' L6='╚══════╝'
  local G1=' ██████╗ ' G2='██╔════╝ ' G3='██║  ███╗' G4='██║   ██║' G5='╚██████╔╝' G6=' ╚═════╝ '
  local P1='██████╗ ' P2='██╔══██╗' P3='██████╔╝' P4='██╔═══╝ ' P5='██║     ' P6='╚═╝     '
  local GT1='████████╗' GT2='╚══██╔══╝' GT3='   ██║   ' GT4='   ██║   ' GT5='   ██║   ' GT6='   ╚═╝   '

  printf '%s%s %s %s %s %s %s %s %s  %s' "$magenta" "$T1" "$E1" "$R1" "$M1" "$I1" "$N1" "$A1" "$L1" "$reset"; printf '%s%s %s %s%s\n' "$red" "$G1" "$P1" "$GT1" "$reset"
  printf '%s%s %s %s %s %s %s %s %s  %s' "$magenta" "$T2" "$E2" "$R2" "$M2" "$I2" "$N2" "$A2" "$L2" "$reset"; printf '%s%s %s %s%s\n' "$red" "$G2" "$P2" "$GT2" "$reset"
  printf '%s%s %s %s %s %s %s %s %s  %s' "$magenta" "$T3" "$E3" "$R3" "$M3" "$I3" "$N3" "$A3" "$L3" "$reset"; printf '%s%s %s %s%s\n' "$red" "$G3" "$P3" "$GT3" "$reset"
  printf '%s%s %s %s %s %s %s %s %s  %s' "$magenta" "$T4" "$E4" "$R4" "$M4" "$I4" "$N4" "$A4" "$L4" "$reset"; printf '%s%s %s %s%s\n' "$red" "$G4" "$P4" "$GT4" "$reset"
  printf '%s%s %s %s %s %s %s %s %s  %s' "$magenta" "$T5" "$E5" "$R5" "$M5" "$I5" "$N5" "$A5" "$L5" "$reset"; printf '%s%s %s %s%s\n' "$red" "$G5" "$P5" "$GT5" "$reset"
  printf '%s%s %s %s %s %s %s %s %s  %s' "$magenta" "$T6" "$E6" "$R6" "$M6" "$I6" "$N6" "$A6" "$L6" "$reset"; printf '%s%s %s %s%s\n' "$red" "$G6" "$P6" "$GT6" "$reset"

  printf '%s  ░▒▓%sTERMINAL%s▓▒░     ░▒▓%sGPT%s▓▒░%s\n' "$cyan" "$magenta" "$reset" "$red" "$reset" "$cyan"
  printf '%s────────────────────────────────────────────────────────────────────────────────────────────%s\n' "$cyan" "$reset"
  printf '%s                 %sTERMINAL-FIRST AI AGENT FOR YOUR SYSTEM%s                 %s\n' "$cyan" "$white" "$reset" "$cyan"
  printf '%s────────────────────────────────────────────────────────────────────────────────────────────%s\n\n' "$cyan" "$reset"
  printf '%sTerminalGPT%s is an %sonline%s terminal-first AI agent.\n' "$white" "$reset" "$white" "$reset"
  printf 'The AI runs in the cloud; your machine only runs the TerminalGPT client and approved commands.\n\n'
  printf '%sThis installer downloads the latest source, creates an isolated Python environment,%s\n' "$gray" "$reset"
  printf 'installs dependencies, then configures an online AI provider.\n\n'

  [[ "${TERMINALGPT_ASSUME_YES:-0}" == "1" ]] && return 0
  [[ -r /dev/tty ]] || { printf '%sUnable to read confirmation from the terminal.%s\n' "$red" "$reset"; return 1; }
  local answer
  while true; do
    printf '%sContinue with installation? [Y/n]: %s' "$cyan" "$reset"
    IFS= read -r answer < /dev/tty || return 1
    answer="${answer:-Y}"
    case "$answer" in
      Y|y|yes|YES|Yes) printf '\n'; return 0 ;;
      N|n|no|NO|No) printf 'Installation cancelled.\n'; return 1 ;;
      *) printf '%sPlease answer Y or N.%s\n' "$red" "$reset" ;;
    esac
  done
}
