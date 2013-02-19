package org.iplantcollaborative.atmo.client.estevewrapper;
import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.net.HttpURLConnection;
import java.net.URL;
import java.net.URLEncoder;
import java.util.ArrayList;
import java.util.HashMap;

public class SriramAPI {
	private static String sriram_GET_request(String urltext) {
		try {
			HttpURLConnection conn;
			URL url = new URL(urltext);
			System.setProperty("http.keepAlive", "false");
			conn = (HttpURLConnection) url.openConnection();
			/* Set header correctly */
			conn.setRequestMethod("GET");
			conn.setRequestProperty("Content-type",
					"application/x-www-form-urlencoded");
			conn.setRequestProperty("Accept", "text/plain");

			int rc = conn.getResponseCode();
			if (rc != 200) {
				System.out.println("Invalid Response");
				return null;
			}

			String line = "";
			String msg = "";
			BufferedReader br = new BufferedReader(new InputStreamReader(
					conn.getInputStream()));
			while ((line = br.readLine()) != null) {
				msg += line;
			}
			return msg;
		} catch (Exception e) {
			return null;
		}
	}

	public static HashMap<String, SInstance> getInstanceList(String key,
			String user) {
		HashMap<String, SInstance> map = new HashMap<String, SInstance>();

		String urltext = "http://crooks.iplantcollaborative.org/getInstanceList?key="
				+ key + "&user=" + user;
		String msg = sriram_GET_request(urltext);
		msg.toString();
		/*
		 * Parse HTML for getInstanceList response.. return list of
		 * name-instance map
		 */

		map.put("fff5c74c8d26", new SInstance("fff5c74c8d26",
				"/78.68/fff5c74c8d26", "emi-8D24142A", "m1.small"));
		map.put("b0acf749b3ce", new SInstance("b0acf749b3ce",
				"/78.63/b0acf749b3ce", "emi-8D24142A", "m1.small"));
		return map;
	}

	public static boolean terminateInstance(String token, String username,
			String userkey) {
		String urltext = "http://crooks.iplantcollaborative.org/terminateInstance?token="
				+ token + "&user=" + username + "&key=" + userkey;
		String msg = sriram_GET_request(urltext);
		return (msg != null && msg.length() > 0);
	}

	public static ArrayList<String> requestInstanceGetToken(String key,
			String username) {
		String token = null;
		String urltext = null;
		try {
			String urlrequest = "http://crooks.iplantcollaborative.org/requestInstance?key="
					+ URLEncoder.encode(key, "UTF-8")
					+ "&user="
					+ URLEncoder.encode(username, "UTF-8");
			String msg = sriram_GET_request(urlrequest);
			int last = 0;
			int count = 0;

			while (last != -1) {
				last = msg.indexOf("<h3>", last + 1);
				if (last != -1) {
					count++;
					if (count == 1) {
						// Parse out the Token
						token = msg.substring(last + "<h3>".length(),
								msg.indexOf("</h3>", last));
					} else {
						// Parse out the URL
						urltext = msg.substring(last + "<h3>".length(),
								msg.indexOf("</h3>", last));
					}
				}
			}
		} catch (Exception e) {
			e.printStackTrace();
		}
		if (token == null || urltext == null)
			return null;

		ArrayList<String> list = new ArrayList<String>();
		list.add(token.substring("Your Vm Token: ".length()));
		list.add(urltext.substring("Your URL: ".length()));
		return list;
	}

	public static String requestKey(String username) {

		String key = null;
		try {
			String msg = sriram_GET_request("http://crooks.iplantcollaborative.org/requestKey?user="
					+ username);
			key = msg.substring(msg.indexOf("<h3>") + 4, msg.indexOf("</h3>"));
			key = key.substring("Your API Key: ".length()
					+ key.indexOf("Your API Key: "));
		} catch (Exception e) {
			;
		}

		return (key);
	}

}
/*
System.out.println("---BEGIN PROTOTYPE API---");
String mykey = SriramAPI.requestKey(username);
System.out.println("Prototype            Key:" + mykey);
ArrayList<String> cred = SriramAPI.requestInstanceGetToken(mykey,
                username);
if (cred == null)
        return;
System.out.println("Prototype Instance Token:" + cred.get(0));
System.out.println("Prototype Instance   URL:" + cred.get(1));
HashMap<String, SInstance> map = SriramAPI.getInstanceList(mykey,
                username);
map.toString();
/* TERMINATE: FOR TESTING/DEBUG PURPOSES * /
if (!SriramAPI.terminateInstance(cred.get(0), username, mykey)) {
        System.out.println("Instance <" + cred.get(0)
                        + "> did not terminate");
}
System.out.println("---END PROTOTYPE API---");
*/
