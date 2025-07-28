# Revision history for Python port of Starman

This is a Python port of the original Perl Starman server. The version number tracks the original, but the changelog below is from the Perl version.

## 0.4017  2023-09-13 13:27:02 PDT
        - Handle EINTR when doing sysread calls (Rob Mueller) #148
        - Requires perl 5.14

## 0.4016  2022-09-13 10:11:34 PDT
        - Add psgix.informational callback #146

## 0.4015  2019-05-20 18:43:46 PDT
        - Fixed a bug incorrectly handling content body of '0' (olsonanl) #133

## 0.4014  2015-06-03 12:01:00 PDT
        - Treat ECONNRESET like EPIPE (i.e. ignore), not as a fatal error #114 (Tim Bunce)

## 0.4013  2015-05-14 15:01:20 PDT
        - Fixed some bad git merges.

## 0.4012  2015-05-14 14:59:48 PDT
        - Add --net_server-* options to pass directly to Net::Server backend (#109)
        - Updated documentation

## 0.4011  2014-11-11 08:07:43 PST
        - Move the app dispatch into a method #107

## 0.4010  2014-08-22 09:37:22 PDT
        - Support --read-timeout #103 (slobo)
        - Handle Expect header case insensitively #101 (oschwald)

## 0.4009  2014-04-03 14:39:27 PDT
        - Do not send chunked body for HEAD requests #87 (therigu)
        - Added --disable-proctitle option to disable the proctitle change #97

## 0.4008  2013-09-08 21:09:22 PDT
        - Make response write loop a zero-copy (ap)

## 0.4007  2013-09-02 17:11:38 PDT
        - Handle EPIPE and stops writing to the socket #84 (ap)
