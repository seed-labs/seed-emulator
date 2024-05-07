# DNS infrastructure binding example

## Step 1:

Run `13-base-component.py`, in order to reuse a base component. In this base component, there are 7 AS, which are `AS150,AS151,AS152,AS153,AS154,AS160,AS161`. Each of AS has 6 hosts. All of hosts are able to connect each other. Each host within their AS has their own local dns server. After running, you will see a base-component.bin file in this folder.


## Step 2:

Run `13-dns-component.py`. In this component, we have pre-built a dns infrastructure, the following shows the zone information.

```
root(.)
	.com
		twitter.com.
		google.com.
	.net
		php.net.
	.edu
		syr.edu.
	.cn
		weibo.cn.
	.gov
		us.gov.
```

Next, we run `13-dns-component-1.py`. In this component, we have pre-built another dns infrastructure, the following shows the zone information.

```
root(.)
	com.
	uk.
		com.uk.
			company.com.uk.
		net.uk.
			example.net.uk.
```

After runing these two component, we will get 2 .bin files in this folder.

## Step 3

In this step, we will run `13-dns-binding-test.py`. Firstly, we need to make sure there are 3 bin files in the folder, then the `13-dns-binding-test.py` will load these 3 bin files, merge dns-component and dns-component-1 , and finally deploy our dns infrastructure into base component.

If everything goes smoothly. You would see there is a folder called `dns-binding` has been generated. Then go to `dns-binding` folder, build and run all container by running `docker-compose build && docker-compose up`.

## Step 4

Let's verify if our dns infrastructure works. Attach into any of hosts, and try to ping www.google.com or www.twitter.com. in each of domain, you would see the resolve results. The another way is to use dig command, try to run `dig .com NS` in any host to see our dns infrastructure distribution.

