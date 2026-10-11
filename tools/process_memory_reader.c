#include <libproc.h>
#include <sys/resource.h>
#include <stdio.h>
#include <stdlib.h>
#include <errno.h>
#include <string.h>
#include <time.h>
#include <mach/mach_time.h>
int main(int argc,char **argv){
 if(argc!=2)return 2;
 char *end;long value=strtol(argv[1],&end,10);if(*end||value<=0)return 2;
 struct rusage_info_v4 usage={0};
 if(proc_pid_rusage((int)value,RUSAGE_INFO_V4,(rusage_info_t*)&usage)!=0){fprintf(stderr,"proc_pid_rusage: %s\n",strerror(errno));return 1;}
 char path[PROC_PIDPATHINFO_MAXSIZE]={0};if(proc_pidpath((int)value,path,sizeof(path))<=0)return 1;
 struct timespec stamp;clock_gettime(CLOCK_REALTIME,&stamp);
 mach_timebase_info_data_t base;mach_timebase_info(&base);
 unsigned long long userNs=(long double)usage.ri_user_time*base.numer/base.denom;
 unsigned long long systemNs=(long double)usage.ri_system_time*base.numer/base.denom;
 printf("{\"pid\":%ld,\"timestamp\":%.6f,\"startAbsoluteTime\":%llu,\"physicalFootprintBytes\":%llu,\"peakPhysicalFootprintBytes\":%llu,\"residentBytes\":%llu,\"userCPUTimeNs\":%llu,\"systemCPUTimeNs\":%llu,\"pageins\":%llu,\"diskReadBytes\":%llu,\"diskWriteBytes\":%llu}\n",value,stamp.tv_sec+stamp.tv_nsec/1e9,usage.ri_proc_start_abstime,usage.ri_phys_footprint,usage.ri_lifetime_max_phys_footprint,usage.ri_resident_size,userNs,systemNs,usage.ri_pageins,usage.ri_diskio_bytesread,usage.ri_diskio_byteswritten);
 return 0;
}
