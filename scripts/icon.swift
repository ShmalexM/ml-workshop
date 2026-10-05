import AppKit
let destination = CommandLine.arguments[1]
let sizes = [(16,1),(16,2),(32,1),(32,2),(128,1),(128,2),(256,1),(256,2),(512,1),(512,2)]
try FileManager.default.createDirectory(atPath: destination, withIntermediateDirectories: true)
for (base, scale) in sizes {
 let size = base * scale
 let image = NSImage(size: NSSize(width:size,height:size))
 image.lockFocus()
 NSColor(calibratedRed:0.03,green:0.57,blue:0.33,alpha:1).setFill()
 let d=CGFloat(size)
 NSBezierPath(roundedRect:NSRect(x:d*0.08,y:d*0.08,width:d*0.84,height:d*0.84),xRadius:d*0.19,yRadius:d*0.19).fill()
 NSColor.white.setStroke()
 let p=NSBezierPath();p.lineWidth=d*0.065;p.lineCapStyle = .round;p.lineJoinStyle = .round
 p.move(to:NSPoint(x:d*0.36,y:d*0.65));p.line(to:NSPoint(x:d*0.22,y:d*0.5));p.line(to:NSPoint(x:d*0.36,y:d*0.35))
 p.move(to:NSPoint(x:d*0.64,y:d*0.65));p.line(to:NSPoint(x:d*0.78,y:d*0.5));p.line(to:NSPoint(x:d*0.64,y:d*0.35))
 p.move(to:NSPoint(x:d*0.55,y:d*0.69));p.line(to:NSPoint(x:d*0.45,y:d*0.31));p.stroke()
 image.unlockFocus()
 let bitmap=NSBitmapImageRep(data:image.tiffRepresentation!)!
 let data=bitmap.representation(using:.png,properties:[:])!
 let suffix=scale==2 ? "@2x" : ""
 try data.write(to:URL(fileURLWithPath:destination+"/icon_\(base)x\(base)\(suffix).png"))
}
