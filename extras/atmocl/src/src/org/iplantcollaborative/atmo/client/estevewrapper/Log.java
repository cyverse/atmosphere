package org.iplantcollaborative.atmo.client.estevewrapper;

import java.io.PrintWriter;
import java.io.StringWriter;
import java.util.Date;

public class Log {
	public static void v (String tag, String msg){System.err.println(new Date().toString()+" - ["+tag+"]:"+msg);}
	public static void d (String tag, String msg){System.out.println(new Date().toString()+" - ["+tag+"]:"+msg);}
	public static void w (String tag, String msg){System.err.println(new Date().toString()+" - ["+tag+"]:"+msg);}
	public static void e (String tag, String msg){System.err.println(new Date().toString()+" - ["+tag+"]:"+msg);}
	public static void e (String tag, String msg, Throwable e){e(tag,msg); e.printStackTrace();}
	public static String getStackTraceString(Exception e) {
		StringWriter res = new StringWriter();
		PrintWriter pw = new PrintWriter(res);
		e.printStackTrace(pw);
		return pw.toString();
	}
	
}
