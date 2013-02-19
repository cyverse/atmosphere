package org.iplantcollaborative.atmo.client.estevewrapper;

import java.io.BufferedInputStream;
import java.io.BufferedReader;
import java.io.BufferedWriter;
import java.io.File;
import java.io.FileWriter;
import java.io.IOException;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.io.Writer;

public class test {

	/**
	 * @param args
	 */
	public static void main(String[] args) {
		// TODO Auto-generated method stub
		Runtime r = Runtime.getRuntime();
		String command = "";
		try {
			BufferedReader bash_out;
			if(AtmoCL.DEBUG) System.out.println(command);
			Process p = r.exec(new String[] { "bash", "-c", command });
			bash_out = new BufferedReader(new InputStreamReader(
					p.getInputStream()));
			String line;
			while((line = bash_out.readLine()) != null) {
				System.out.println(line);
			}
		}catch(Exception e) {e.printStackTrace();}
	}

}
