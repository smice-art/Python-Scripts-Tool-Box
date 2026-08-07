# Bake Geometry Nodes Setup

this little tools help you to bake a animation from a Geometry Node Setup. 

# Instruction

Usually you can´t export  a geometry node setup to an external file (except alembic & nlp). I made this to make a shape key copy of my geometry node setup including the animation. Be aware that you set a "Realize Instances" if you have a Instance on Point node in your setup. if everything is proper set up and you animation runs without problems, just paste the script in the text editor, mark your animation object and press "Run". depending on the frames and complexity of your setup it could take a while. than you find a new object in your overview with "bake" in the name. you can delete the rest and can export it to fbx or whatever format your like (and support animations)