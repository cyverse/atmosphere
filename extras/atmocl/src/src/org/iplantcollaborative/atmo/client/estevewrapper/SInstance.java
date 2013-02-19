package org.iplantcollaborative.atmo.client.estevewrapper;
public class SInstance {
	String token, url, image, size;

	public SInstance(String token, String url, String image, String size) {
		super();
		this.token = token;
		this.url = url;
		this.image = image;
		this.size = size;
	}

	public String getToken() {
		return token;
	}

	public void setToken(String token) {
		this.token = token;
	}

	public String getUrl() {
		return url;
	}

	public void setUrl(String url) {
		this.url = url;
	}

	public String getImage() {
		return image;
	}

	public void setImage(String image) {
		this.image = image;
	}

	public String getSize() {
		return size;
	}

	public void setSize(String size) {
		this.size = size;
	}

	@Override
	public String toString() {
		return "SInstance [token=" + token + ", url=" + url + ", image="
				+ image + ", size=" + size + "]";
	}

}
