from urlparse import urlparse
from threading import Thread
import httplib, sys, os, requests, signal, random, time
from Queue import Queue


concurrent = 50
timeoutWindow = 4
path = './homebrew-cask/Casks'
results = []

taskDict = {}
timeoutsList = []

def toNum(n):
    try:
        if n.isdigit() is False:
            return False

        return float(n)
    except ValueError:
        return False


def doCheckVersion(current_url, v_check_version, orig_request):
    v_check_url = current_url.replace('#{version}', v_check_version)
    try:
        r = requests.head(v_check_url, timeout=timeoutWindow)
    except Exception:
        r = None
        pass

    if r is not None:
        if r.headers.get('content-type') == orig_request.headers.get('content-type'):
            return v_check_version

    return None

def doWork():
    while True:
    # while len(taskDict) > 0:
        item = q.get()
        orig_url = item[0]
        orig_version = item[1]
        the_split = item[2]
        current_url = item[3]
        homepage_url = item[4]
        filename = item[5]
        index = item[6]
        # orig_url, orig_version, the_split, current_url, homepage_url, filename, index

        try:
            orig_request = requests.head(orig_url, timeout=timeoutWindow)
        except Exception:
            timeoutsList.append( (filename[:-3], homepage_url, orig_version) )
            del taskDict[filename[:-3]]
            q.task_done()
            continue

        bad_version = str( int(the_split[0] ) + 5) + '.' + str( random.randint(100,9999) )
        bad_url = current_url.replace('#{version}', bad_version)
        try:
            bad_request = requests.head(bad_url, timeout=timeoutWindow)
        except Exception:
            timeoutsList.append( (filename[:-3], homepage_url, orig_version) )
            del taskDict[filename[:-3]]
            q.task_done()
            continue


        #sometimes content-type doesnt' exist, so we have to check
        if ( str(orig_request.status_code)[0] in ('2','3') and
            orig_request.headers.get('content-type') and
            bad_request.headers.get('content-type') ):

            #make sure we can tell good from bad - we compare the content type to see if an erroneous request will produce a different content-type from a request we know is good
            if bad_request.headers['content-type'] != orig_request.headers['content-type']:

                possibleNewVersions = []

                if len(the_split) is 2:
                    for n in xrange(1,4):
                        v_check_version_maj = str( int(the_split[0] ) + n) + '.0'
                        v_check_version_min = str(the_split[0]) +'.'+ str( int(the_split[1] ) + n)

                        if doCheckVersion(current_url, v_check_version_maj, orig_request) is not None:
                            possibleNewVersions.append(v_check_version_maj)
                        if doCheckVersion(current_url, v_check_version_min, orig_request) is not None:
                            possibleNewVersions.append(v_check_version_min)


                if len(the_split) is 3:
                    for n in xrange(1,6):
                        v_check_version_maj = str( int(the_split[0] ) + n) + '.0.0'
                        v_check_version_min = str(the_split[0]) +'.'+ str( int(the_split[1])+n ) +'.0'
                        v_check_version_patch = str(the_split[0]) +'.'+ str(the_split[1]) +'.'+ str( int(the_split[2] ) + n)

                        if doCheckVersion(current_url, v_check_version_maj, orig_request) is not None:
                            possibleNewVersions.append(v_check_version_maj)
                        if doCheckVersion(current_url, v_check_version_min, orig_request) is not None:
                            possibleNewVersions.append(v_check_version_min)
                        if doCheckVersion(current_url, v_check_version_patch, orig_request) is not None:
                            possibleNewVersions.append(v_check_version_patch)



                if len(possibleNewVersions):
                    print '#'+str(index)+' - ' + filename[:-3] + ' - ' + orig_version

                    print "\thompage url: ", homepage_url
                    print "\tcurrent url: ", orig_url
                    print "\tnew versions: ", possibleNewVersions
                    print

                    # mydict = {}
                    # mydict['index'] = str(index)
                    # mydict['cask'] = filename[:-3]
                    # mydict['orig_version'] = orig_version
                    # mydict['homepage_url'] = homepage_url
                    # mydict['orig_url'] = orig_url
                    # mydict['possibleNewVersions'] = possibleNewVersions

                    # results.append(mydict)




        # print index, filename, "task done"
        del taskDict[filename[:-3]]
        # print len(taskDict)
        # if len(taskDict) < 10:
            # print taskDict
        q.task_done()

start = time.clock()
q = Queue(concurrent * 2)
for i in range(concurrent):
    t = Thread(target=doWork)
    t.daemon = True
    t.start()
try:
    # for index, filename in enumerate( sorted(os.listdir(path), key=str.lower)[:1500] ):
    for index, filename in enumerate( sorted(os.listdir(path), key=str.lower) ):
        with open(path+'/'+filename,"r") as fi:


            version_start_string = "version "
            url_start_string = "url "
            homepage_start_string = "homepage "
            current_version = []
            current_url = ""
            version_lines_list = []
            url_lines_list = []
            homepage_lines_list = []
            isUsableVersion = False
            keepGoing = False

            #build lists for later... not agreat way to do this but it works for now
            for ln in fi:
                ln = ln.strip()
                if ln.startswith(version_start_string):
                    version_lines_list.append(ln)
                    
                if ln.startswith(url_start_string):
                    url_lines_list.append(ln)
                    
                if ln.startswith(homepage_start_string):
                    homepage_lines_list.append(ln)

            for i in version_lines_list:
                prep = i[len(version_start_string):].translate(None, '\'')
                if prep != ':latest':
                    version_split = prep.split('.')
                    if len(version_split) in xrange(2,4):
                        areAcceptableDigits = True;

                        for v in version_split:
                            test_num = toNum(v)
                            if test_num > 99 or test_num is False:
                                areAcceptableDigits = False


                        if areAcceptableDigits:
                            current_version.append(prep)

            for i in url_lines_list:
                if '#{version}' in i and '#{version.' not in i:
                    isUsableVersion = True
                    current_url = i[len(url_start_string):].translate(None, '\"')

            for i in homepage_lines_list:
                homepage_url = i[len(homepage_start_string):].translate(None, '\'')

            if isUsableVersion and len(current_version) is 1:
                orig_version = current_version[0]
                the_split = orig_version.split('.')
                versions_to_try = []
                keepGoing = True

            #only doing major.minor and major.minor.patch versions right now
            if keepGoing == True and len(the_split) in (2,3):
                orig_url = current_url.replace('#{version}', orig_version)

                taskDict[filename[:-3]] = filename[:-3]

                q.put( (orig_url, orig_version, the_split, current_url, homepage_url, filename, index) )

    q.join()
except Exception:
    print "exception, exiting"
    sys.exit(1)

# print results
print 'list of timeouts:'
for i in timeoutsList:
    print i[0], i[2]
    print i[1]
    print

print 'time taken: '+str(int(time.clock()) - int(start))+'s'


