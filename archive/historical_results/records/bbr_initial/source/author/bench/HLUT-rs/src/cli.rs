use clap::{Args, Parser, Subcommand, ValueEnum};

#[derive(Parser)]
#[command(name = "hlut", about = "Launch the benchmarks")]
pub(crate) struct Cli {
    #[command(subcommand)]
    pub(crate) cmd: Cmd,
}

#[derive(Subcommand)]
pub(crate) enum Cmd {
    Full(Opts),
    Partial(Opts),
}

#[derive(Args)]
pub(crate) struct Opts {
    #[arg(long)]
    pub(crate) perror: usize,

    #[arg(long, value_enum)]
    pub(crate) mode: Mode,
}

#[derive(Clone, ValueEnum)]
pub(crate) enum Mode {
    Paper,
    Regenerated,
}

pub(crate) fn mode_string(mode: Mode) -> String {
    match mode {
        Mode::Paper => "paper".to_owned(),
        Mode::Regenerated => "regenerated".to_owned(),
    }
}
