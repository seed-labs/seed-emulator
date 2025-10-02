
dockerID=$(docker ps | grep $name | awk '{print $1}')
   
if [[ -f ${name}_bird.conf_${postfix} ]]; then
   echo "== Copy original bird.conf to the container: $name"
   docker cp ${name}_bird.conf_${postfix} $dockerID:/etc/bird/bird.conf 

   echo "== Execute 'birdc configure' on the container"
   docker exec $dockerID birdc configure
else 
   echo "** File ${name}_bird.conf_${postfix} does not exist"
fi

