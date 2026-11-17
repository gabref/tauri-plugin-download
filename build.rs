const COMMANDS: &[&str] = &[
   "create",
   "list",
   "get",
   "start",
   "cancel",
   "pause",
   "resume",
   "is_native",
   "register_listener",
   "remove_listener",
];

fn main() {
   // These flags supply the integration test executable's manifest.
   // Tauri's desktop mock links Common Controls v6, which Windows must select
   // before the test process can start.
   if std::env::var("CARGO_CFG_TARGET_OS").as_deref() == Ok("windows")
      && std::env::var("CARGO_CFG_TARGET_ENV").as_deref() == Ok("msvc")
   {
      println!("cargo:rustc-link-arg-tests=/MANIFEST:EMBED");
      println!(
         "cargo:rustc-link-arg-tests=/MANIFESTDEPENDENCY:type='win32' \
          name='Microsoft.Windows.Common-Controls' version='6.0.0.0' \
          processorArchitecture='*' publicKeyToken='6595b64144ccf1df' language='*'"
      );
   }

   tauri_plugin::Builder::new(COMMANDS)
      .android_path("android")
      .ios_path("ios")
      .build();
}
