# VHS tape for schema-drift demo. Render with:  vhs demo/demo.tape
Output demo/demo.gif

Set Shell "bash"
Set FontSize 16
Set Width 1300
Set Height 800
Set Theme "Catppuccin Mocha"
Set Padding 20
Set TypingSpeed 45ms
Set LoopOffset 60%

Hide
Type "export PATH=/tmp/demoenv/bin:$PATH && cd $(mktemp -d) && cp -r ~/oss-repos/schema-drift/examples . && clear" Enter
Show

Type "# schema-drift: data contracts that fail CI on breaking changes" Sleep 1s Enter
Type "schema-drift snapshot examples/orders_v1.json --name orders" Sleep 500ms Enter
Sleep 2.5s

Type "# a safe change (new column) -> exit 0" Sleep 800ms Enter
Type "schema-drift check examples/orders_v2_safe.json --name orders" Sleep 500ms Enter
Sleep 3s

Type "# a breaking change (dropped column) -> exit 1, fails the build" Sleep 800ms Enter
Type "schema-drift check examples/orders_v3_breaking.json --name orders" Sleep 500ms Enter
Sleep 4s
