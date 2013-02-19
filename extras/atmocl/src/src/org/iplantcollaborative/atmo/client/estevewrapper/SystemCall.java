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

public class SystemCall {

	static String printCommand(String command) {
		Runtime r = Runtime.getRuntime();
		String message = "";
		try {

			Process p = r.exec(command);
			InputStream in = p.getInputStream();
			BufferedInputStream buf = new BufferedInputStream(in);
			InputStreamReader inread = new InputStreamReader(buf);
			BufferedReader bufferedreader = new BufferedReader(inread);
			String line;
			while ((line = bufferedreader.readLine()) != null) {
				message += line + "\n";
			}
			return message;
		} catch (Exception e) {
			if (AtmoCL.DEBUG)
				System.out.println(e.getMessage());
		}
		return null;
	}

	public static BufferedReader runCommand(String command) {
		Runtime r = Runtime.getRuntime();
		try {
			Process p = r.exec(command);
			InputStream in = p.getInputStream();
			BufferedInputStream buf = new BufferedInputStream(in);
			InputStreamReader inread = new InputStreamReader(buf);
			BufferedReader bufferedreader = new BufferedReader(inread);
			return bufferedreader;
		} catch (IOException e) {
			if (AtmoCL.DEBUG)
				System.out.println(e.getMessage());
		}
		return null;
	}

	public static int returnCodePipe(String command) {
		Runtime r = Runtime.getRuntime();
		try {
			Process p = r.exec(new String[] { "bash", "-c", command });
			InputStream in = p.getInputStream();
			int exitVal = p.waitFor();
			if (exitVal != 0)
				exitVal = p.exitValue();
			if (AtmoCL.DEBUG) {
				BufferedReader bash_out = new BufferedReader(
						new InputStreamReader(in));
				String line;
				while ((line = bash_out.readLine()) != null) {
					System.out.println(line);
				}
			}
			return exitVal;
		} catch (Exception e) {
			if (AtmoCL.DEBUG)
				System.out.println(e.getMessage());
		}
		return -999;
	}

	public static BufferedReader runPipeCommand(String command) {
		Runtime r = Runtime.getRuntime();
		try {
			BufferedReader bash_out;
			Process p = r.exec(new String[] { "bash", "-c", command });
			bash_out = new BufferedReader(new InputStreamReader(
					p.getInputStream()));
			// p.waitFor();
			return bash_out;
		} catch (Exception e) {
			if (AtmoCL.DEBUG)
				System.out.println(e.getMessage());
		}
		return null;
	}
	public static BufferedReader runPipeCommand_err(String command) {
		Runtime r = Runtime.getRuntime();
		try {
			BufferedReader bash_err;
			Process p = r.exec(new String[] { "bash", "-c", command });
			bash_err = new BufferedReader(new InputStreamReader(
					p.getErrorStream()));
			// p.waitFor();
			return bash_err;
		} catch (Exception e) {
			if (AtmoCL.DEBUG)
				System.out.println(e.getMessage());
		}
		return null;
	}
	public static int returnCode(String command) {
		Runtime r = Runtime.getRuntime();
		try {
			Process p = r.exec(command);
			int exitVal = p.waitFor();
			return exitVal;
		} catch (Exception e) {
			if (AtmoCL.DEBUG)
				System.out.println(e.getMessage());
		}
		return -999;
	}

	static void createAndWrite(String fname, String text) {
		Writer writer = null;
		File file = null;
		try {

			file = new File(fname);
			if (file.exists()) {
				return;
			}

			writer = new BufferedWriter(new FileWriter(file));
			writer.write(text);
		} catch (Exception e) {
			if (AtmoCL.DEBUG)
				e.printStackTrace();
		} finally {
			try {
				if (writer != null) {
					writer.close();
					file.setExecutable(true);
				}
			} catch (IOException e) {
				if (AtmoCL.DEBUG)
					e.printStackTrace();
			}

		}
	}
}
