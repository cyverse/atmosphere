#!/bin/bash

################################################################
#
#  Script to backup or retrieve data between an Atmosphere
#  instance and iPlant Datastore
#  
#  iplant_backup.sh -- Version 1.0
#  Sangeeta Kuchimanchi -- 01/28/2014
#
################################################################

user=`whoami`
USER_LOCAL_DIR="/home/$user"
USER_DS_DIR="/iplant/home/$user"
USER_ATMO_DIR="/iplant/home/$user/atmosphere"
IRODS_ENV_FILE="/home/$user/.irods/.irodsEnv"
IRODS_DIR="/home/$user/.irods"
ATMO_BACKUP="atmo_backup"

function logging
{
   data=$1
   echo `date` "  " $data >> $HOME/.irods/iplant-backup.log
}


function check_exists
{

  FILE=$1
  PROTOCOL=$2

  if [ $PROTOCOL == "restore" ]
  then
 
    if [ -f $FILE ]
    then
       echo "1"
    elif [ -d $FILE ]
    then
       echo "1"
    else
       echo "0"
    fi
 
  fi

  if [ $PROTOCOL == "backup" ]
  then

    irods_file=`echo $FILE | sed 's,'"$USER_LOCAL_DIR"',,'`


    if [ ! $irods_file == "/" ] 
    then
  
       check_for_default=`echo $irods_file | grep $ATMO_BACKUP`    
  
       if [ ! $check_for_default ]   
       then

          exists=`ils $USER_DS_DIR | grep $irods_file`
 
          if [ $exists ]
          then
             echo "1"
          else
             echo "0"
          fi    

       else
 
          without_atmo=`echo $irods_files | sed 's,'"\/$ATMO_BACKUP\/"',,'`
          check_for_folder=`ils $USER_DS_DIR | grep $ATMO_BACKUP | grep "C-" | sed 's/C-//g' | sed 's,'"$USER_DS_FOLDER\/"',,'`
      
          if [ $check_for_folder ]
          then

             exists=`ils $USER_ATMO_DIR | grep $without_atmo`
             if [ $exists ]
             then
                echo "1"
             else
                echo "0"
             fi

          else
             echo "2"
          fi
       
       fi

    else
      
       echo "3"

    fi

  fi

}


function set_env
{

user=`whoami`

if [ -d $IRODS_DIR ]
then

if [ ! -f $IRODS_ENV_FILE ]
then

cat > $IRODS_ENV_FILE <<EOF
irodsHost data.iplantcollaborative.org
irodsPort 1247
irodsUserName $user
irodsZone iplant
EOF

set_env

else
echo "1"

fi

else

mkdir $HOME/.irods
set_env

fi

}
    

if [ $user != "root" ]
then

   echo
   echo -n "Do you want to backup or restore local instance/volume data?[backup/restore]:  "
   read protocol
   echo

   case $protocol in 
       
        "backup")
  
           echo -n "Specify local file/directory's full path on the instance [eg: $USER_LOCAL_DIR, $USER_LOCAL_DIR/file.txt]: " 
           read source
           echo
           echo -n "Specify file/directory path on iPlant datastore [eg: $USER_DS_DIR, $USER_DS_DIR/file.txt][Default is $USER_ATMO_DIR] : "
           read destination
           echo
   
           if [ ! $destination ]
           then

              destination="$USER_ATMO_DIR"
           fi
           
           output=`set_env`
           if [ $output == "1" ]
           then

              if [ ! $source ]
              then

                 echo
                 echo "ERROR: Local directory path is empty"
                 echo
             
              else
               
                 exists=`check_exists $source $protocol`

                 if [ $exists == "1" ]
                 then

                   iinit
                   output=`iput -r $source $destination`

                   logging "Transfer request: Username:$user Protocol:$protocol, $source:$destination, Output: $output"

                 elif [ $exists == "2" ]
                 then

                   echo
                   echo "$USER_ATMO_DIR not found. Creating atmosphere folder....."
                   echo
                   iinit
                   imkdir $USER_ATMO_DIR
                   output=`iput -r $source $destination`

                   logging "Transfer request: Username:$user Protocol:$protocol, $source:$destination, Output: $output"   

                 elif [ $exists == "3" ]
                 then

                   echo -n "You are trying to backup your home directory $USER_LOCAL_DIR.Do you want to continue [yes/no]: "
                   read answer
                   echo

                   if [ $answer == "yes" ]
                   then

                      iinit
                      output=`iput -rf $source $destination`
                      logging "Transfer request: Username:$user Protocol:$protocol, $source:$destination, Output: $output"

                   else

                      exit 1

                   fi

                 else

                   echo -n "The file/folder already exists on the datastore. Do you want to overwrite?[yes/no]: "
                   read answer
                   echo

                   if [ $answer == "yes" ]
                   then

                      iinit
                      output=`iput -rf $source $destination`
                      logging "Transfer request: Username:$user Protocol:$protocol, $source:$destination, Output: $output"

                   else

                      exit 1

                   fi

                 fi

              fi

           else

              echo
              echo " Your iRODS env was not set correctly. Please run "iinit" and try again"
              echo

           fi

           ;;


        "restore")
 
           echo -n "Specify file/directory's full path on iPlant datastore [eg: $USER_DS_DIR, $USER_DS_DIR/file.txt]: "
           read source
           echo
           echo -n "Specify local file/directory's full path on the instance [eg: $USER_LOCAL_DIR, $USER_LOCAL_DIR/file.txt]: "
           read destination
           echo

           FILE=`/bin/basename $source`
           FILE_EXISTS="$destination/$FILE"
         
           output=`set_env`
           if [ $output == "1" ]
           then

              if [ ! $source ] || [ ! $destination ]
              then
                 
                 echo
                 echo "ERROR: Source/Destination path is empty"
                 echo

              else

                 exists=`check_exists $FILE_EXISTS $protocol`
                 if [ $exists == "0" ]
                 then

                   iinit
                   output=`iget -r $source $destination`

                   logging "Transfer request: Username:$user Protocol:$protocol, $source:$destination, Output: $output"
                
                 else

                   echo -n "The file/folder already exists. Do you want to overwrite?[yes/no]: "
                   read answer
                   echo
                   
                   if [ $answer == "yes" ]
                   then
                   
                      iinit
                      output=`iget -rf $source $destination`
                      logging "Transfer request: Username:$user Protocol:$protocol, $source:$destination, Output: $output"
                   
                   else

                      exit 1
 
                   fi

                 fi

              fi
           
           else
     
              echo
              echo " Your iRODS env was not set correctly. Please run "iinit" and try again"
              echo

           fi

           ;;

        *)

           echo
           echo 'ERROR: No input found. Please enter "backup" or "restore"'
           echo
           echo "This script helps backup or retrieve data between an Atmosphere instance and iPlant Datastore"
           echo
           echo "[restore]: This will get the data from iPlant datastore to your instance"
           echo
           echo "[backup]: This will put the data from your instance to the iPlant datastore"
           echo
           echo "If you have any issues or questions please email support@iplantcollaborative.org"
           echo
           exit 1

   esac

else

   echo
   echo 'ERROR: This script cannot be run as "root" user'
   echo
   exit 1

fi

