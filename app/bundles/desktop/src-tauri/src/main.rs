// Prevents additional console window on Windows in release, DO NOT REMOVE!!
#![cfg_attr(
  all(not(debug_assertions), target_os = "windows"),
  windows_subsystem = "windows"
)]

use tauri::api::process::{Command, CommandEvent};
use tauri::Manager;
use std::time::Duration;
use async_std::task;

fn main() {
  tauri::Builder::default()
    .setup(|app| {
      let splashscreen_window = app.get_window("splashscreen").unwrap();
      let main_window = app.get_window("main").unwrap();
      let error_main_window = main_window.clone(); 

      let (mut rx, _child) = Command::new_sidecar("trame")
        .expect("failed to create sidecar")
        .args(["--server", "--port", "0", "--timeout", "1", "--no-http"])
        .spawn()
        .expect("Failed to spawn server");

      tauri::async_runtime::spawn(async move {
        while let Some(event) = rx.recv().await {
          match event {
            CommandEvent::Stdout(line) => {
              println!("[Trame STDOUT]: {}", line);
              if line.contains("tauri-server-port=") {
                let tokens: Vec<&str> = line.split("=").collect();
                if tokens.len() > 1 {
                  let port_token = tokens[1].to_string();
                  let port = port_token.trim();
                  println!("[Rust DEBUG]: Detected port: {}", port);
                  let _ = main_window.eval(&format!("window.location.replace(window.location.href + '?sessionURL=ws://localhost:{}/ws')", port));
                } else {
                  println!("[Rust ERROR]: Malformed tauri-server-port line: {}", line);
                }
              }
              if line.contains("tauri-client-ready") {
                println!("[Rust DEBUG]: tauri-client-ready detected");
                task::sleep(Duration::from_secs(2)).await;
                splashscreen_window.close().unwrap();
                main_window.show().unwrap();
                main_window.set_focus().unwrap();
                println!("[Rust DEBUG]: Main window shown");
              }
            }
            CommandEvent::Stderr(line) => {
              eprintln!("[Trame STDERR]: {}", line);
            }
            CommandEvent::Error(error_message) => {
              eprintln!("[Trame ERROR]: {}", error_message);
              let _ = error_main_window.eval(&format!("alert('Sidecar Error: {}');", error_message.replace("'", "\\'")));
            }
            CommandEvent::Terminated(payload) => {
              eprintln!("[Trame TERMINATED]: Code: {:?}, Signal: {:?}", payload.code, payload.signal);
              if payload.code != Some(0) {
                let _ = error_main_window.eval(&format!("alert('Sidecar Terminated Unexpectedly: Code {:?}, Signal {:?}');", payload.code, payload.signal));
              }
            }
            _ => {
                println!("[Trame OTHER_EVENT]: {:?}", event);
            }
          }
        }
        println!("[Rust DEBUG]: Sidecar event loop ended.");
      });
      Ok(())
    })
    .run(tauri::generate_context!())
    .expect("error while running application");
}
